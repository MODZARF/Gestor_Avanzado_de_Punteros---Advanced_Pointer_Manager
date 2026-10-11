# -*- coding: utf-8 -*-
import os
import re
import json
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class BinaryEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Avanzado de Punteros y Strings - By ZARF")
        self.root.geometry("1150x840")
        self.root.minsize(950, 750)
        
        # Estilos visuales refinados
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', font=('Segoe UI', 9))
        self.style.configure('Header.TLabel', font=('Segoe UI', 11, 'bold'), foreground='#1a365d')
        self.style.configure('Status.TLabel', font=('Segoe UI', 9, 'italic'), foreground='#4a5568')
        self.style.configure('Action.TButton', font=('Segoe UI', 10, 'bold'), foreground='white', background='#2b6cb0')
        self.style.map('Action.TButton', background=[('active', '#2c5282')])
        self.style.configure('Revert.TButton', font=('Segoe UI', 9, 'bold'), foreground='white', background='#e53e3e')
        self.style.map('Revert.TButton', background=[('active', '#c53030')])
        
        # Rutas de archivos e información de estado
        self.bin_path = None
        self.txt_path = None
        self.table_path = None
        self.history_json_path = None
        self.char_table = {}      
        self.inverse_table = {}   
        
        # Estructuras de datos
        self.txt_data = []  
        self.selected_sec1_item = None
        self.selected_sec2_item = None
        self.current_pointer_offsets = []  
        
        # HISTORIAL en memoria para reversión
        self.history_log = {}
        self.current_left_view = 0 # 0: Actual, 1: Original
        
        # Estado temporal para la reversión diferida del String
        self.pending_string_reversion = {}
        
        # Inicializar Componentes de la Interfaz
        self.create_widgets()
        
    def create_widgets(self):
        # ----------------------------------------------------
        # PANEL SUPERIOR COMPACTO
        # ----------------------------------------------------
        top_frame = ttk.Frame(self.root, padding="4")
        top_frame.pack(fill=tk.X, side=tk.TOP)
        
        self.btn_open_bin = ttk.Button(top_frame, text="📁 ABRIR ARCHIVO", command=self.open_binary_file)
        self.btn_open_bin.pack(side=tk.LEFT, padx=3)
        
        self.lbl_bin_status = ttk.Label(top_frame, text="Ningún archivo binario cargado", style='Status.TLabel')
        self.lbl_bin_status.pack(side=tk.LEFT, padx=5)
        
        self.btn_apply = ttk.Button(top_frame, text="💾 APLICAR CAMBIOS", style='Action.TButton', command=self.apply_changes)
        self.btn_apply.pack(side=tk.LEFT, padx=4)
        
        self.btn_revert = ttk.Button(top_frame, text="⏪ REVERTIR PTR", style='Revert.TButton', command=self.revert_change, state=tk.DISABLED)
        self.btn_revert.pack(side=tk.LEFT, padx=2)

        self.btn_swap_ptr = ttk.Button(top_frame, text="⇄ INVERTIR PTR", command=self.swap_pointers_in_memory)
        self.btn_swap_ptr.pack(side=tk.LEFT, padx=2)

        self.btn_about = ttk.Button(top_frame, text="ℹ️ Acerca de", command=self.show_about_info)
        self.btn_about.pack(side=tk.LEFT, padx=10)
        
        table_frame = ttk.Frame(top_frame)
        table_frame.pack(side=tk.RIGHT, padx=3)
        
        self.btn_open_table = ttk.Button(table_frame, text="📋 ABRIR TABLA", command=self.open_table_file)
        self.btn_open_table.pack(anchor=tk.NE)
        
        self.lbl_table_status = ttk.Label(table_frame, text="Tabla: NO cargada", style='Status.TLabel', foreground='#c53030')
        self.lbl_table_status.pack(anchor=tk.NE)

        main_container = ttk.Frame(self.root, padding="6")
        main_container.pack(fill=tk.BOTH, expand=True)

        # ----------------------------------------------------
        # SECCIÓN 1: Selección ORIGEN
        # ----------------------------------------------------
        sec1_frame = ttk.LabelFrame(main_container, text=" SECCIÓN 1: SELECCIÓN ORIGEN (BÚSQUEDA DE PUNTEROS A REEMPLAZAR) ", padding="6")
        sec1_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        self.setup_search_subpanel(sec1_frame, section_num=1)

        # ----------------------------------------------------
        # SECCIÓN 2: Selección DESTINO
        # ----------------------------------------------------
        sec2_frame = ttk.LabelFrame(main_container, text=" SECCIÓN 2: SELECCIÓN DESTINO (EDICIÓN DE STRINGS Y ASIGNACIÓN DE PUNTEROS) ", padding="6")
        sec2_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        self.setup_search_subpanel(sec2_frame, section_num=2)

        # ----------------------------------------------------
        # PANEL INFERIOR CENTRAL ADAPTADO (Listbox + Copias)
        # ----------------------------------------------------
        bottom_panel = ttk.Frame(main_container)
        bottom_panel.pack(fill=tk.X, side=tk.BOTTOM, pady=2)
        
        bottom_panel.columnconfigure(0, weight=1)
        bottom_panel.columnconfigure(1, weight=2)
        bottom_panel.columnconfigure(2, weight=1)
        
        # Bloque Izquierdo: Ubicación del Puntero (Listbox + Controles Copiables)
        self.ptr_match_frame = ttk.LabelFrame(bottom_panel, text=" Información de offsets de punteros (Sec 1 en Binario) ", padding="4")
        self.ptr_match_frame.grid(row=0, column=0, sticky="nsew", padx=3)
        
        nav_frame = ttk.Frame(self.ptr_match_frame)
        nav_frame.pack(fill=tk.X, pady=1)
        
        self.btn_prev_view = ttk.Button(nav_frame, text="◀", width=3, command=lambda: self.switch_left_view(-1), state=tk.DISABLED)
        self.btn_prev_view.pack(side=tk.LEFT)
        
        self.lbl_view_title = ttk.Label(nav_frame, text="VISTA: ACTUAL", font=('Segoe UI', 8, 'bold'), foreground='#2b6cb0')
        self.lbl_view_title.pack(side=tk.LEFT, expand=True)
        
        self.btn_next_view = ttk.Button(nav_frame, text="▶", width=3, command=lambda: self.switch_left_view(1), state=tk.DISABLED)
        self.btn_next_view.pack(side=tk.RIGHT)
        
        # Contenedor con Entry copiable para el puntero seleccionado de Sec 1
        ptr_copy_frame = ttk.Frame(self.ptr_match_frame)
        ptr_copy_frame.pack(fill=tk.X, anchor=tk.W, pady=2)
        ttk.Label(ptr_copy_frame, text="Ptr S1 Act:", font=('Segoe UI', 8, 'bold')).pack(side=tk.LEFT)
        self.copied_ptr_sec1_var = tk.StringVar(value="-")
        self.entry_copied_ptr_sec1 = ttk.Entry(ptr_copy_frame, textvariable=self.copied_ptr_sec1_var, font=('Consolas', 9), width=12, state='readonly')
        self.entry_copied_ptr_sec1.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        
        self.ptr_offsets_listbox = tk.Listbox(self.ptr_match_frame, height=3, font=('Consolas', 9), exportselection=False)
        self.ptr_offsets_listbox.pack(fill=tk.BOTH, expand=True, pady=1)
        self.ptr_offsets_listbox.bind("<<ListboxSelect>>", self.on_listbox_offset_changed)
        
        offset_controls_frame = ttk.Frame(self.ptr_match_frame)
        offset_controls_frame.pack(fill=tk.X, pady=2)
        
        self.chk_all_offsets_var = tk.BooleanVar(value=False)
        self.chk_all_offsets = ttk.Checkbutton(offset_controls_frame, text="Aplica a TODOS", variable=self.chk_all_offsets_var)
        self.chk_all_offsets.pack(side=tk.LEFT, padx=1)
        
        self.copied_offset_var = tk.StringVar(value="")
        self.entry_copied_offset = ttk.Entry(offset_controls_frame, textvariable=self.copied_offset_var, width=12, font=('Consolas', 9))
        self.entry_copied_offset.pack(side=tk.RIGHT, padx=3, fill=tk.X, expand=True)

        # Bloque Central: Cuadro de Edición de String
        string_edit_frame = ttk.LabelFrame(bottom_panel, text=" Edición e Inspección del String en el Binario ", padding="4")
        string_edit_frame.grid(row=0, column=1, sticky="nsew", padx=3)
        
        meta_string_frame = ttk.Frame(string_edit_frame)
        meta_string_frame.pack(fill=tk.X)
        
        self.lbl_str_offset = ttk.Label(meta_string_frame, text="Offset Str: -", font=('Segoe UI', 8, 'bold'))
        self.lbl_str_offset.pack(side=tk.LEFT, padx=3)
        
        self.lbl_str_len_info = ttk.Label(meta_string_frame, text="Límite: 0 / 0", font=('Segoe UI', 8, 'bold'), foreground='#2b6cb0')
        self.lbl_str_len_info.pack(side=tk.RIGHT, padx=3)
        
        self.str_entry_var = tk.StringVar()
        self.str_entry_var.trace_add("write", self.validate_string_length)
        self.entry_string = ttk.Entry(string_edit_frame, textvariable=self.str_entry_var, font=('Segoe UI', 10))
        self.entry_string.pack(fill=tk.X, pady=3, padx=3)
        
        self.btn_revert_str = ttk.Button(string_edit_frame, text="⏪ REVERTIR STRING", style='Revert.TButton', command=self.prepare_string_reversion, state=tk.DISABLED)
        self.btn_revert_str.pack(anchor=tk.E, padx=3, pady=1)
        
        # Bloque Derecho: Flujo de Punteros
        new_ptr_frame = ttk.LabelFrame(bottom_panel, text=" Flujo Automático de Punteros ", padding="4")
        new_ptr_frame.grid(row=0, column=2, sticky="nsew", padx=3)
        
        manual_frame = ttk.Frame(new_ptr_frame)
        manual_frame.pack(fill=tk.X, pady=1)
        
        self.chk_manual_var = tk.BooleanVar(value=False)
        self.chk_manual = ttk.Checkbutton(manual_frame, text="Manual", variable=self.chk_manual_var, command=self.toggle_manual_pointer)
        self.chk_manual.pack(side=tk.LEFT, padx=1)
        
        self.manual_ptr_var = tk.StringVar()
        self.manual_ptr_var.trace_add("write", lambda *args: self.update_pointer_flow_label())
        self.entry_manual_ptr = ttk.Entry(manual_frame, textvariable=self.manual_ptr_var, width=10, font=('Consolas', 9), state=tk.DISABLED)
        self.entry_manual_ptr.pack(side=tk.RIGHT, padx=3, expand=True, fill=tk.X)
        
        self.lbl_ptr_flow_info = ttk.Label(new_ptr_frame, text="Seleccione filas para calcular.", font=('Segoe UI', 8, 'italic'), justify=tk.LEFT)
        self.lbl_ptr_flow_info.pack(fill=tk.BOTH, expand=True, pady=2, padx=3)

    def setup_search_subpanel(self, parent, section_num):
        search_control_frame = ttk.Frame(parent)
        search_control_frame.pack(fill=tk.X, pady=2)
        ttk.Label(search_control_frame, text="Buscar:").pack(side=tk.LEFT, padx=1)
        
        search_var = tk.StringVar()
        entry_search = ttk.Entry(search_control_frame, textvariable=search_var, width=22)
        entry_search.pack(side=tk.LEFT, padx=3)
        
        chk_offset_var = tk.BooleanVar(value=True)
        chk_len_var = tk.BooleanVar(value=True)
        chk_ptr_var = tk.BooleanVar(value=True)
        chk_str_var = tk.BooleanVar(value=True)
        chk_mod_var = tk.BooleanVar(value=False) # Nuevo filtro para líneas modificadas
        
        ttk.Checkbutton(search_control_frame, text="Offset", variable=chk_offset_var).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(search_control_frame, text="Longitud", variable=chk_len_var).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(search_control_frame, text="Puntero", variable=chk_ptr_var).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(search_control_frame, text="String", variable=chk_str_var).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(search_control_frame, text="Mod", variable=chk_mod_var).pack(side=tk.LEFT, padx=2) # Checkbutton visual
        
        # Agregamos 'modified' al contexto de búsqueda
        search_context = {
            'var': search_var, 
            'offset': chk_offset_var, 
            'length': chk_len_var, 
            'pointer': chk_ptr_var, 
            'string': chk_str_var,
            'modified': chk_mod_var
        }
        
        btn_search = ttk.Button(search_control_frame, text="🔍", width=3, command=lambda: self.execute_search_filter(section_num, search_context))
        btn_search.pack(side=tk.LEFT, padx=3)
        ttk.Button(search_control_frame, text="🔄 Todo", command=lambda: self.reset_section_view(section_num, search_context)).pack(side=tk.LEFT, padx=1)

        if section_num == 1:
            ttk.Button(search_control_frame, text="🔗 Sinc. Abajo", command=self.sync_section2_with_section1).pack(side=tk.LEFT, padx=4)
        elif section_num == 2:
            ttk.Button(search_control_frame, text="🔗 Sinc. Arriba", command=self.sync_section1_with_section2).pack(side=tk.LEFT, padx=4)



        entry_search.bind("<Return>", lambda event: self.execute_search_filter(section_num, search_context))

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        
        columns = ("offset", "length", "pointer", "string")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=4)
        tree.heading("offset", text="Offset String")
        tree.heading("length", text="Len")
        tree.heading("pointer", text="Puntero")
        tree.heading("string", text="String Contenido")
        
        tree.column("offset", width=100, anchor=tk.CENTER)
        tree.column("length", width=60, anchor=tk.CENTER)
        tree.column("pointer", width=120, anchor=tk.CENTER)
        tree.column("string", width=500, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        if section_num == 1:
            tree.bind("<<TreeviewSelect>>", self.on_select_section1)
            self.tree_sec1 = tree
        else:
            tree.bind("<<TreeviewSelect>>", self.on_select_section2)
            self.tree_sec2 = tree

    def load_history_from_disk(self):
        self.history_log.clear()
        if not self.bin_path: return
        base_path, _ = os.path.splitext(self.bin_path)
        self.history_json_path = base_path + "_historial.json"
        if os.path.exists(self.history_json_path):
            try:
                with open(self.history_json_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    self.history_log = {int(k): v for k, v in raw_data.items()}
            except Exception as e: messagebox.showwarning("Historial", str(e))

    def save_history_to_disk(self):
        if not self.history_json_path: return
        try:
            with open(self.history_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.history_log, f, indent=4, ensure_ascii=False)
        except Exception as e: print(f"Error guardando historial: {e}")

    def toggle_manual_pointer(self):
        if self.chk_manual_var.get():
            self.entry_manual_ptr.configure(state=tk.NORMAL)
        else:
            self.entry_manual_ptr.configure(state=tk.DISABLED)
        self.update_pointer_flow_label()

    def on_listbox_offset_changed(self, event):
        selected_idx = self.ptr_offsets_listbox.curselection()
        if selected_idx and self.current_pointer_offsets:
            idx = selected_idx[0]
            if idx < len(self.current_pointer_offsets):
                self.copied_offset_var.set(f"0x{self.current_pointer_offsets[idx]:08X}")
        else:
            self.copied_offset_var.set("")

    def switch_left_view(self, direction):
        if not self.selected_sec1_item: return
        self.current_left_view += direction
        if self.current_left_view < 0: self.current_left_view = 0
        if self.current_left_view > 1: self.current_left_view = 1
        item_id = self.selected_sec1_item['id']
        
        if self.current_left_view == 0:
            self.lbl_view_title.configure(text="VISTA: ACTUAL", foreground='#2b6cb0')
            self.copied_ptr_sec1_var.set(self.selected_sec1_item['pointer'].upper())
            self.scan_binary_for_pointer_matches(self.selected_sec1_item['pointer'])
        else:
            self.lbl_view_title.configure(text="VISTA: ORIGINAL", foreground='#e53e3e')
            hist = self.history_log[item_id]
            self.copied_ptr_sec1_var.set(hist['old_pointer'].upper())
            self.ptr_offsets_listbox.delete(0, tk.END)
            for off in hist.get('offsets', []):
                self.ptr_offsets_listbox.insert(tk.END, f"Original Off: 0x{off:08X}")
            self.copied_offset_var.set("")
        self.update_nav_buttons_state()

    def update_nav_buttons_state(self):
        if self.selected_sec1_item:
            item_id = self.selected_sec1_item['id']
            if item_id in self.history_log and 'old_pointer' in self.history_log[item_id]:
                if self.current_left_view == 0:
                    self.btn_prev_view.configure(state=tk.DISABLED)
                    self.btn_next_view.configure(state=tk.NORMAL)
                else:
                    self.btn_prev_view.configure(state=tk.NORMAL)
                    self.btn_next_view.configure(state=tk.DISABLED)
                return
        self.btn_prev_view.configure(state=tk.DISABLED)
        self.btn_next_view.configure(state=tk.DISABLED)

    def sync_section2_with_section1(self):
        if not self.selected_sec1_item:
            messagebox.showwarning("Sincronización", "Primero debe seleccionar una fila en la Sección 1.")
            return
        target_id = self.selected_sec1_item['id']
        if self.tree_sec2.exists(target_id):
            self.tree_sec2.selection_set(target_id)
            self.tree_sec2.see(target_id)
            self.on_select_section2(None)
        else:
            messagebox.showwarning("Sincronización", "La línea está oculta por filtro en Sección 2.")

    def sync_section1_with_section2(self):
        """Sincroniza la selección de la Sección 1 con la fila seleccionada en la Sección 2."""
        if not self.selected_sec2_item:
            messagebox.showwarning("Sincronización", "Primero debe seleccionar una fila en la Sección 2.")
            return
        target_id = self.selected_sec2_item['id']
        if self.tree_sec1.exists(target_id):
            self.tree_sec1.selection_set(target_id)
            self.tree_sec1.see(target_id)
            self.on_select_section1(None)
        else:
            messagebox.showwarning("Sincronización", "La línea está oculta por filtro en Sección 1.")

    def swap_pointers_in_memory(self):
        """Invierte directamente en el binario y descriptor los punteros de las selecciones en Sec 1 y Sec 2."""
        if not self.bin_path or not self.txt_path:
            messagebox.showwarning("Invertir Punteros", "Debe cargar un archivo binario primero.")
            return

        if not self.selected_sec1_item or not self.selected_sec2_item:
            messagebox.showwarning("Invertir Punteros", "Debe seleccionar una fila activa en AMBAS secciones para poder invertir los punteros.")
            return

        item1 = self.selected_sec1_item
        item2 = self.selected_sec2_item

        ptr1 = item1['pointer'].strip().replace(" ", "").upper()
        ptr2 = item2['pointer'].strip().replace(" ", "").upper()

        if item1['id'] == item2['id']:
            messagebox.showwarning("Invertir Punteros", "Ha seleccionado la misma fila en ambas secciones.")
            return

        if ptr1 == ptr2:
            messagebox.showinfo("Invertir Punteros", "Ambas filas ya tienen el mismo puntero, no hay nada que invertir.")
            return

        # Confirmación de seguridad
        confirm = messagebox.askyesno(
            "Invertir Punteros", 
            f"¿Desea invertir estos punteros directamente en el binario?\n\n"
            f"• Fila {item1['id']} ({item1['offset']}): {ptr1} ➔ {ptr2}\n"
            f"• Fila {item2['id']} ({item2['offset']}): {ptr2} ➔ {ptr1}"
        )

        if not confirm:
            return

        try:
            # 1. Escanear offsets donde residen ambos punteros en el binario
            bytes_ptr1 = bytes.fromhex(ptr1)
            bytes_ptr2 = bytes.fromhex(ptr2)

            with open(self.bin_path, 'rb') as rb:
                content = rb.read()

            offsets_p1 = []
            idx = content.find(bytes_ptr1)
            while idx != -1:
                offsets_p1.append(idx)
                idx = content.find(bytes_ptr1, idx + 1)

            offsets_p2 = []
            idx = content.find(bytes_ptr2)
            while idx != -1:
                offsets_p2.append(idx)
                idx = content.find(bytes_ptr2, idx + 1)

            # 2. Registrar en historial para poder revertir si fuera necesario
            id1, id2 = item1['id'], item2['id']
            if id1 not in self.history_log: self.history_log[id1] = {}
            if 'old_pointer' not in self.history_log[id1]:
                self.history_log[id1]['old_pointer'] = ptr1
                self.history_log[id1]['offsets'] = list(offsets_p1)
            self.history_log[id1]['offsets_written_history'] = list(offsets_p1)

            if id2 not in self.history_log: self.history_log[id2] = {}
            if 'old_pointer' not in self.history_log[id2]:
                self.history_log[id2]['old_pointer'] = ptr2
                self.history_log[id2]['offsets'] = list(offsets_p2)
            self.history_log[id2]['offsets_written_history'] = list(offsets_p2)

            self.save_history_to_disk()

            # 3. Escribir intercambio directo en el binario (ptr1 pasa a ser ptr2 y viceversa)
            with open(self.bin_path, 'r+b') as wb:
                for off in offsets_p1:
                    wb.seek(off)
                    wb.write(bytes_ptr2)
                for off in offsets_p2:
                    wb.seek(off)
                    wb.write(bytes_ptr1)

            # 4. Actualizar estructuras en memoria (txt_data)
            item1['pointer'] = ptr2
            item2['pointer'] = ptr1

            # 5. Actualizar descriptor .txt
            updated_txt_lines = []
            with open(self.txt_path, 'r', encoding='utf-8', errors='replace') as r_txt:
                for line in r_txt:
                    parts = line.strip('\r\n').split('\t')
                    if len(parts) >= 4:
                        curr_off = parts[0].strip().lower()
                        if curr_off == item1['offset'].strip().lower():
                            parts[2] = ptr2
                        elif curr_off == item2['offset'].strip().lower():
                            parts[2] = ptr1
                        updated_txt_lines.append("\t".join(parts) + "\n")
                    else:
                        updated_txt_lines.append(line)

            with open(self.txt_path, 'w', encoding='utf-8') as w_txt:
                w_txt.writelines(updated_txt_lines)

            # 6. Refrescar los Treeviews en pantalla
            if self.tree_sec1.exists(id1):
                self.tree_sec1.item(id1, values=(item1['offset'], item1['length'], item1['pointer'], item1['string']))
            if self.tree_sec2.exists(id1):
                self.tree_sec2.item(id1, values=(item1['offset'], item1['length'], item1['pointer'], item1['string']))

            if self.tree_sec1.exists(id2):
                self.tree_sec1.item(id2, values=(item2['offset'], item2['length'], item2['pointer'], item2['string']))
            if self.tree_sec2.exists(id2):
                self.tree_sec2.item(id2, values=(item2['offset'], item2['length'], item2['pointer'], item2['string']))

            # Refrescar vista actual
            self.copied_ptr_sec1_var.set(item1['pointer'].upper())
            self.scan_binary_for_pointer_matches(item1['pointer'])
            self.update_pointer_flow_label()

            messagebox.showinfo("Éxito", "¡Punteros invertidos y guardados en el binario correctamente!")

        except Exception as e:
            messagebox.showerror("Error", f"Fallo al invertir punteros: {str(e)}")


        #Si modifica este script por favor mantén los créditos :)
    def show_about_info(self):
        messagebox.showinfo("Acerca de", "Gestor de punteros V4\n==Diseñado por ZARF==\nProgramado con Gemini AI")


    def open_binary_file(self):
        file_selected = filedialog.askopenfilename(title="Seleccionar Archivo Binario Primario", filetypes=[("Todos los archivos", "*.*")])
        if not file_selected: return
        if file_selected.lower().endswith('.txt'):
            messagebox.showerror("Error", "Seleccione un archivo binario válido (.txt no permitido).")
            return
        base_path, _ = os.path.splitext(file_selected)
        expected_txt = base_path + ".txt"
        if not os.path.exists(expected_txt):
            messagebox.showerror("Error", f"Falta descriptor:\n'{expected_txt}'")
            return
        self.bin_path = file_selected
        self.txt_path = expected_txt
        self.lbl_bin_status.configure(text=f"Binario: {os.path.basename(self.bin_path)}")
        self.parse_descriptor_txt()
        self.load_history_from_disk()

    def open_table_file(self):
        file_selected = filedialog.askopenfilename(title="Cargar Tabla de Caracteres", filetypes=[("Archivos de Texto", "*.txt")])
        if not file_selected: return
        try:
            new_table, new_inverse = {}, {}
            with open(file_selected, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip('\r\n')
                    if '=' in line:
                        parts = line.split('=', 1)
                        if parts[0]:
                            new_table[parts[0]] = parts[1]
                            new_inverse[parts[1]] = parts[0]
            self.table_path = file_selected
            self.char_table, self.inverse_table = new_table, new_inverse
            self.lbl_table_status.configure(text="Tabla: Cargada", foreground='#2f855a')
            if self.selected_sec2_item: self.load_item_into_editors(self.selected_sec2_item)
        except Exception as e: messagebox.showerror("Error", str(e))

    def parse_descriptor_txt(self):
        self.txt_data.clear()
        try:
            with open(self.txt_path, 'r', encoding='utf-8', errors='replace') as f:
                for idx, line in enumerate(f, 1):
                    line = line.strip('\r\n')
                    if not line: continue
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        self.txt_data.append({
                            'id': idx, 'offset': parts[0].strip(), 'length': parts[1].strip(),
                            'pointer': parts[2].strip(), 'string': parts[3]
                        })
            self.populate_treeview(self.tree_sec1, self.txt_data)
            self.populate_treeview(self.tree_sec2, self.txt_data)
        except Exception as e: messagebox.showerror("Error", str(e))

    def populate_treeview(self, tree_widget, data_list):
        for row in tree_widget.get_children(): tree_widget.delete(row)
        for item in data_list:
            tree_widget.insert("", tk.END, iid=item['id'], values=(item['offset'], item['length'], item['pointer'], item['string']))

    def execute_search_filter(self, section_num, context):
        query = context['var'].get().strip().lower()
        tree = self.tree_sec1 if section_num == 1 else self.tree_sec2
        only_modified = context['modified'].get()
        
        # Si no hay texto de búsqueda Y tampoco está marcado "Mod", reseteamos la vista
        if not query and not only_modified:
            self.populate_treeview(tree, self.txt_data)
            return
            
        filtered_results = []
        for item in self.txt_data:
            # 1. Validación de Filtro de Modificados
            if only_modified and item['id'] not in self.history_log:
                continue # Si se pide solo modificados y esta id no está en el JSON, se ignora
                
            # 2. Validación de Criterios de Texto (Solo si el usuario escribió algo)
            if query:
                match_found = False
                if context['offset'].get() and query in item['offset'].lower(): match_found = True
                if context['length'].get() and query in item['length'].lower(): match_found = True
                if context['pointer'].get() and query in item['pointer'].lower(): match_found = True
                if context['string'].get() and query in item['string'].lower(): match_found = True
                
                if not match_found:
                    continue # Si se buscaba texto y no coincidió con nada, se ignora
                    
            filtered_results.append(item)
            
        self.populate_treeview(tree, filtered_results)

    def reset_section_view(self, section_num, context):
        context['var'].set("")
        context['modified'].set(False) # Desmarcar filtro modificado también al limpiar todo
        self.populate_treeview(self.tree_sec1 if section_num == 1 else self.tree_sec2, self.txt_data)

    def update_pointer_flow_label(self):
        p1 = self.selected_sec1_item['pointer'].upper() if self.selected_sec1_item else "Ninguno"
        if self.chk_manual_var.get():
            p2 = self.manual_ptr_var.get().strip().upper()
            if not p2: p2 = "[Vacío]"
        else:
            p2 = self.selected_sec2_item['pointer'].upper() if self.selected_sec2_item else "Ninguno"
        
        info_text = f"🎯 [ORIGEN] Ptr S1: {p1}\n📍 [DESTINO] Ptr Act: {p2}\n🔄 ACCIÓN: "
        if self.selected_sec1_item and (self.selected_sec2_item or self.chk_manual_var.get()):
            if not self.chk_manual_var.get() and self.selected_sec1_item['id'] == self.selected_sec2_item['id']:
                info_text += "Misma línea.\nNo cambiará puntero."
            else: info_text += f"Reemplazar {p1} por {p2}."
        else: info_text += "Seleccione filas."
        self.lbl_ptr_flow_info.configure(text=info_text, font=('Segoe UI', 8, 'bold' if self.selected_sec1_item else 'italic'))

    def on_select_section1(self, event):
        selected = self.tree_sec1.selection()
        if selected:
            item_id = int(selected[0])
            self.selected_sec1_item = next((item for item in self.txt_data if item['id'] == item_id), None)
            self.current_left_view = 0
            self.lbl_view_title.configure(text="VISTA: ACTUAL", foreground='#2b6cb0')
            self.copied_offset_var.set("")
            
            if self.selected_sec1_item:
                self.copied_ptr_sec1_var.set(self.selected_sec1_item['pointer'].upper())
                self.scan_binary_for_pointer_matches(self.selected_sec1_item['pointer'])
                
                is_modified = item_id in self.history_log
                self.btn_revert.configure(state=tk.NORMAL if is_modified and 'old_pointer' in self.history_log[item_id] else tk.DISABLED)
            
            self.update_nav_buttons_state()
            self.update_pointer_flow_label()

    def scan_binary_for_pointer_matches(self, pointer_hex_str):
        self.ptr_offsets_listbox.delete(0, tk.END)
        self.current_pointer_offsets.clear()
        if not self.bin_path: return
        try: 
            pointer_bytes = bytes.fromhex(pointer_hex_str.replace(" ", ""))
        except ValueError: return
        try:
            with open(self.bin_path, 'rb') as f: 
                content = f.read()
            idx = content.find(pointer_bytes)
            while idx != -1:
                self.current_pointer_offsets.append(idx)
                self.ptr_offsets_listbox.insert(tk.END, f"Offset: 0x{idx:08X}")
                idx = content.find(pointer_bytes, idx + 1)
            if self.current_pointer_offsets: 
                self.ptr_offsets_listbox.select_set(0)
                self.on_listbox_offset_changed(None)
        except Exception: pass

    def on_select_section2(self, event):
        selected = self.tree_sec2.selection()
        if selected:
            item_id = int(selected[0])
            self.selected_sec2_item = next((item for item in self.txt_data if item['id'] == item_id), None)
            if self.selected_sec2_item: 
                self.load_item_into_editors(self.selected_sec2_item)
                
                is_str_modified = item_id in self.history_log and 'old_string_bytes' in self.history_log[item_id]
                is_pending = item_id in self.pending_string_reversion
                self.btn_revert_str.configure(state=tk.NORMAL if is_str_modified and not is_pending else tk.DISABLED)
            self.update_pointer_flow_label()

    def load_item_into_editors(self, item):
        if not self.bin_path: return
        try:
            offset_val = int(item['offset'], 16)
            max_bytes_to_read = int(item['length'])
        except ValueError: return
        try:
            with open(self.bin_path, 'rb') as rb:
                rb.seek(offset_val)
                raw_buffer = rb.read(max_bytes_to_read)
            end_idx = raw_buffer.find(b'\x00')
            clean_buffer = raw_buffer[:end_idx] if end_idx != -1 else raw_buffer
            decoded_string = clean_buffer.decode('utf-8', errors='replace')
        except Exception: decoded_string = item['string']

        if self.char_table:
            decoded_string = "".join([self.inverse_table.get(char, char) for char in decoded_string])

        self.lbl_str_offset.configure(text=f"Offset Str: 0x{item['offset'].upper()}")
        self.str_entry_var.set(decoded_string)
        self.lbl_str_len_info.configure(text=f"Límite: {len(decoded_string)} / {max_bytes_to_read}")

    def validate_string_length(self, *args):
        if not self.selected_sec2_item: return
        try:
            max_allowed = int(self.selected_sec2_item['length'])
            raw_text = self.str_entry_var.get()
            mapped_text = "".join([self.char_table.get(c, c) for c in raw_text])
            current_len = len(mapped_text.encode('utf-8', errors='replace'))
            self.lbl_str_len_info.configure(text=f"Bytes: {current_len} / {max_allowed}")
            self.lbl_str_len_info.configure(foreground='#c53030' if current_len > max_allowed else '#2b6cb0')
        except ValueError: pass

    def prepare_string_reversion(self):
        if not self.selected_sec2_item: return
        item_id = self.selected_sec2_item['id']
        if item_id not in self.history_log or 'old_string_bytes' not in self.history_log[item_id]: return
        
        hist = self.history_log[item_id]
        self.pending_string_reversion[item_id] = {
            'bytes': bytes.fromhex(hist['old_string_bytes']),
            'text': hist['original_descriptor_text'],
            'offset': hist['string_offset_used']
        }
        self.str_entry_var.set(hist['original_descriptor_text'])
        self.btn_revert_str.configure(state=tk.DISABLED)
        messagebox.showinfo("Preparación", "Texto de fábrica cargado. Presione 'APLICAR CAMBIOS' para guardarlo físicamente.")

    def apply_changes(self):
        if not self.bin_path or not self.selected_sec1_item:
            messagebox.showwarning("Atención", "Faltan selecciones o archivo binario.")
            return

        id_sec1 = self.selected_sec1_item['id']
        item_sec1 = self.selected_sec1_item
        current_descriptor_ptr = item_sec1['pointer'].strip().replace(" ", "").upper()

        if self.chk_manual_var.get():
            new_pointer_hex = self.manual_ptr_var.get().strip().replace(" ", "").upper()
            if not new_pointer_hex: messagebox.showerror("Error", "Puntero manual vacío."); return
        else:
            if not self.selected_sec2_item: messagebox.showwarning("Atención", "Seleccione Sección 2."); return
            new_pointer_hex = self.selected_sec2_item['pointer'].strip().replace(" ", "").upper()

        is_ptr_changing = (current_descriptor_ptr != new_pointer_hex)
        if is_ptr_changing and id_sec1 in self.history_log and 'old_pointer' in self.history_log[id_sec1]:
            if current_descriptor_ptr != self.history_log[id_sec1]['old_pointer'].upper():
                messagebox.showerror("Seguridad", "Este puntero ya fue modificado.\nDebe presionar 'REVERTIR PTR' para poder cambiarlo de nuevo.")
                return

        if not re.match(r"^[0-9a-fA-F]+$", new_pointer_hex) or len(new_pointer_hex) % 2 != 0:
            messagebox.showerror("Error", "Puntero hexadecimal inválido.")
            return

        offsets_to_write = []
        if is_ptr_changing:
            if self.chk_all_offsets_var.get():
                offsets_to_write = list(self.current_pointer_offsets)
                if not offsets_to_write: messagebox.showerror("Error", "No hay offsets válidos."); return
            else:
                selected_idx = self.ptr_offsets_listbox.curselection()
                if not selected_idx or self.current_left_view == 1:
                    messagebox.showerror("Error", "Seleccione un offset en la listbox (Vista ACTUAL)."); return
                offsets_to_write.append(self.current_pointer_offsets[selected_idx[0]])

        final_string_buffer = None
        target_string_offset = None
        id_sec2 = None
        new_string_raw = None
        is_reverting_str = False

        if self.selected_sec2_item and not self.chk_manual_var.get():
            item_sec2 = self.selected_sec2_item
            id_sec2 = item_sec2['id']
            new_string_raw = self.str_entry_var.get()
            try: max_len = int(item_sec2['length'])
            except ValueError: return

            if id_sec2 in self.pending_string_reversion:
                is_reverting_str = True
                final_string_buffer = self.pending_string_reversion[id_sec2]['bytes']
                target_string_offset = self.pending_string_reversion[id_sec2]['offset']
                new_string_raw = self.pending_string_reversion[id_sec2]['text']
            else:
                if new_string_raw != item_sec2['string']:
                    if id_sec2 in self.history_log and 'old_string_bytes' in self.history_log[id_sec2]:
                        messagebox.showerror("Seguridad", "Este String ya fue modificado.\nDebe revertirlo antes de otra edición.")
                        return
                    mapped_string = "".join([self.char_table.get(char, char) for char in new_string_raw])
                    encoded_string_bytes = mapped_string.encode('utf-8', errors='replace')
                    if len(encoded_string_bytes) > max_len:
                        messagebox.showerror("Error", f"Excede los {max_len} bytes."); return
                    final_string_buffer = encoded_string_bytes + (b'\x00' * (max_len - len(encoded_string_bytes)))
                    target_string_offset = int(item_sec2['offset'], 16)

        try:
            if is_ptr_changing:
                if id_sec1 not in self.history_log: self.history_log[id_sec1] = {}
                if 'old_pointer' not in self.history_log[id_sec1]:
                    self.history_log[id_sec1]['old_pointer'] = current_descriptor_ptr
                    self.history_log[id_sec1]['offsets'] = list(self.current_pointer_offsets)
                self.history_log[id_sec1]['offsets_written_history'] = list(offsets_to_write)

            if final_string_buffer is not None and id_sec2 is not None and not is_reverting_str:
                if id_sec2 not in self.history_log: self.history_log[id_sec2] = {}
                if 'old_string_bytes' not in self.history_log[id_sec2]:
                    with open(self.bin_path, 'rb') as rb:
                        rb.seek(target_string_offset)
                        original_str_bytes = rb.read(max_len)
                    self.history_log[id_sec2]['old_string_bytes'] = original_str_bytes.hex()
                    self.history_log[id_sec2]['string_offset_used'] = target_string_offset
                    self.history_log[id_sec2]['string_length_used'] = max_len
                    self.history_log[id_sec2]['original_descriptor_text'] = item_sec2['string']

            if is_reverting_str:
                if id_sec2 in self.history_log:
                    del self.history_log[id_sec2]['old_string_bytes']
                    del self.history_log[id_sec2]['string_offset_used']
                    del self.history_log[id_sec2]['string_length_used']
                    del self.history_log[id_sec2]['original_descriptor_text']
                    if not self.history_log[id_sec2]: del self.history_log[id_sec2]
                if id_sec2 in self.pending_string_reversion: del self.pending_string_reversion[id_sec2]

            self.save_history_to_disk()

            with open(self.bin_path, 'r+b') as wb:
                if final_string_buffer is not None:
                    wb.seek(target_string_offset)
                    wb.write(final_string_buffer)
                for off in offsets_to_write:
                    wb.seek(off)
                    wb.write(bytes.fromhex(new_pointer_hex))
                
            updated_txt_lines = []
            with open(self.txt_path, 'r', encoding='utf-8', errors='replace') as r_txt:
                for line in r_txt:
                    parts = line.strip('\r\n').split('\t')
                    if len(parts) >= 4:
                        curr_off = parts[0].strip().lower()
                        if curr_off == item_sec1['offset'].strip().lower() and is_ptr_changing:
                            parts[2] = new_pointer_hex.upper()
                        if final_string_buffer is not None and id_sec2 and curr_off == self.txt_data[id_sec2-1]['offset'].strip().lower():
                            parts[3] = new_string_raw
                        updated_txt_lines.append("\t".join(parts) + "\n")
                    else: updated_txt_lines.append(line)
            with open(self.txt_path, 'w', encoding='utf-8') as w_txt: w_txt.writelines(updated_txt_lines)

            messagebox.showinfo("Éxito", "Cambios guardados con éxito.")
            self.chk_all_offsets_var.set(False)
            
            if is_ptr_changing: item_sec1['pointer'] = new_pointer_hex.upper()
            if final_string_buffer is not None and id_sec2: 
                self.txt_data[id_sec2-1]['string'] = new_string_raw
            
            if self.tree_sec1.exists(id_sec1):
                self.tree_sec1.item(id_sec1, values=(item_sec1['offset'], item_sec1['length'], item_sec1['pointer'], item_sec1['string']))
            if final_string_buffer is not None and id_sec2 and self.tree_sec2.exists(id_sec2):
                self.tree_sec2.item(id_sec2, values=(self.txt_data[id_sec2-1]['offset'], self.txt_data[id_sec2-1]['length'], self.txt_data[id_sec2-1]['pointer'], self.txt_data[id_sec2-1]['string']))

            self.scan_binary_for_pointer_matches(item_sec1['pointer'])
            self.on_select_section1(None)
            if id_sec2 and self.selected_sec2_item: self.on_select_section2(None)
        except Exception as e: messagebox.showerror("Error", f"Fallo al inyectar: {str(e)}")

    def revert_change(self):
        if not self.selected_sec1_item: return
        item_id = self.selected_sec1_item['id']
        if item_id not in self.history_log or 'old_pointer' not in self.history_log[item_id]: return
        
        if messagebox.askyesno("Revertir Puntero", "¿Restaurar puntero original de fábrica?"):
            hist = self.history_log[item_id]
            target_pointer = hist['old_pointer']
            written_offsets = list(hist['offsets_written_history'])
            
            try:
                with open(self.bin_path, 'r+b') as wb:
                    for off in written_offsets:
                        wb.seek(off)
                        wb.write(bytes.fromhex(target_pointer))
                        
                updated_txt_lines = []
                with open(self.txt_path, 'r', encoding='utf-8', errors='replace') as r_txt:
                    for line in r_txt:
                        parts = line.strip('\r\n').split('\t')
                        if len(parts) >= 4 and parts[0].strip().lower() == self.selected_sec1_item['offset'].strip().lower():
                            parts[2] = target_pointer.upper()
                            updated_txt_lines.append("\t".join(parts) + "\n")
                        else: updated_txt_lines.append(line)
                with open(self.txt_path, 'w', encoding='utf-8') as w_txt: w_txt.writelines(updated_txt_lines)
                
                del self.history_log[item_id]['old_pointer']
                del self.history_log[item_id]['offsets']
                del self.history_log[item_id]['offsets_written_history']
                if not self.history_log[item_id]: del self.history_log[item_id]
                self.save_history_to_disk()
                
                self.selected_sec1_item['pointer'] = target_pointer.upper()
                if self.tree_sec1.exists(item_id):
                    self.tree_sec1.item(item_id, values=(self.selected_sec1_item['offset'], self.selected_sec1_item['length'], self.selected_sec1_item['pointer'], self.selected_sec1_item['string']))
                
                self.current_left_view = 0
                self.scan_binary_for_pointer_matches(self.selected_sec1_item['pointer'])
                self.on_select_section1(None)
                messagebox.showinfo("Éxito", "Puntero restaurado.")
            except Exception as e: messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = BinaryEditorApp(root)
    root.mainloop()
