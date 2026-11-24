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
        self.root.title("Gestor Avanzado de Punteros y Strings - By ZARF (v4.4)")
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
        self.style.configure('StringEdit.TButton', font=('Segoe UI', 10, 'bold'), foreground='white', background='#2f855a')
        self.style.map('StringEdit.TButton', background=[('active', '#276749')])
        self.style.configure('Revert.TButton', font=('Segoe UI', 10, 'bold'), foreground='white', background='#e53e3e')
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
        
        # Padding detectado para el string actualmente seleccionado en Sección 2
        self.current_item_padding = 0
        
        # Referencias y bandera de sincronización para el editor expandido
        self.expanded_window = None
        self.expanded_text_widget = None
        self._syncing_editors = False
        
        # Inicializar Componentes de la Interfaz
        self.create_widgets()

    # ----------------------------------------------------
    # UTILIDADES DE CONVERSIÓN DE SALTOS DE LÍNEA
    # ----------------------------------------------------
    @staticmethod
    def to_escaped_nl(text):
        if not text: return ""
        return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")

    @staticmethod
    def to_real_nl(escaped_text):
        if not escaped_text: return ""
        return escaped_text.replace("\\n", "\n")

    def create_widgets(self):
        # ----------------------------------------------------
        # PANEL SUPERIOR COMPACTO
        # ----------------------------------------------------
        top_frame = ttk.Frame(self.root, padding="4")
        top_frame.pack(fill=tk.X, side=tk.TOP)
        
        self.btn_open_bin = ttk.Button(top_frame, text="📁 ABRIR ARCHIVO", command=self.handle_binary_button)
        self.btn_open_bin.pack(side=tk.LEFT, padx=3)
        
        self.lbl_bin_status = ttk.Label(top_frame, text="Ningún archivo binario cargado", style='Status.TLabel')
        self.lbl_bin_status.pack(side=tk.LEFT, padx=5)
        
        self.btn_apply = ttk.Button(top_frame, text="🎯 CAMBIAR PTR", style='Action.TButton', command=self.apply_changes)
        self.btn_apply.pack(side=tk.LEFT, padx=4)
        
        self.btn_revert = ttk.Button(top_frame, text="⏪ REVERTIR PTR", style='Revert.TButton', command=self.revert_change, state=tk.DISABLED)
        self.btn_revert.pack(side=tk.LEFT, padx=2)

        self.btn_swap_ptr = ttk.Button(top_frame, text="⇄ INVERTIR PTR", command=self.swap_pointers_in_memory)
        self.btn_swap_ptr.pack(side=tk.LEFT, padx=2)

        self.btn_about = ttk.Button(top_frame, text="ℹ️ Acerca de", command=self.show_about_info)
        self.btn_about.pack(side=tk.LEFT, padx=10)
        
        right_top_frame = ttk.Frame(top_frame)
        right_top_frame.pack(side=tk.RIGHT, padx=3)
        
        self.btn_tools = ttk.Button(right_top_frame, text="🛠️ HERRAMIENTAS", command=self.open_tools_window)
        self.btn_tools.pack(side=tk.LEFT, padx=3)
        
        table_control_frame = ttk.Frame(right_top_frame)
        table_control_frame.pack(side=tk.LEFT, padx=3)
        
        self.btn_open_table = ttk.Button(table_control_frame, text="📋 ABRIR TABLA", command=self.handle_table_button)
        self.btn_open_table.pack(anchor=tk.NE)
        
        self.lbl_table_status = ttk.Label(table_control_frame, text="Tabla: NO cargada", style='Status.TLabel', foreground='#c53030')
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
        # PANEL INFERIOR CENTRAL ADAPTADO
        # ----------------------------------------------------
        bottom_panel = ttk.Frame(main_container)
        bottom_panel.pack(fill=tk.X, side=tk.BOTTOM, pady=2)
        
        bottom_panel.columnconfigure(0, weight=1)
        bottom_panel.columnconfigure(1, weight=2)
        bottom_panel.columnconfigure(2, weight=1)
        
        # Bloque Izquierdo
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
        
        self.lbl_str_len_info = ttk.Label(meta_string_frame, text="Bytes: 0 / 0", font=('Segoe UI', 8, 'bold'), foreground='#2b6cb0')
        self.lbl_str_len_info.pack(side=tk.RIGHT, padx=3)
        
        self.str_entry_var = tk.StringVar()
        self.str_entry_var.trace_add("write", self.on_main_entry_changed)
        self.entry_string = ttk.Entry(string_edit_frame, textvariable=self.str_entry_var, font=('Segoe UI', 10))
        self.entry_string.pack(fill=tk.X, pady=3, padx=3)

        self.entry_string.bind("<Return>", self.on_main_entry_enter)
        self.entry_string.bind("<KP_Enter>", self.on_main_entry_enter)
        self.entry_string.bind("<BackSpace>", self.on_main_entry_backspace)
        self.entry_string.bind("<Delete>", self.on_main_entry_delete)
        
        str_btn_frame = ttk.Frame(string_edit_frame)
        str_btn_frame.pack(fill=tk.X, padx=3, pady=1)

        self.btn_main_copy = ttk.Button(str_btn_frame, text="Copiar", width=6, command=self.main_copy_string)
        self.btn_main_copy.pack(side=tk.LEFT, padx=2)

        self.btn_main_paste = ttk.Button(str_btn_frame, text="Pegar", width=6, command=self.main_paste_string)
        self.btn_main_paste.pack(side=tk.LEFT, padx=2)

        self.btn_main_clear = ttk.Button(str_btn_frame, text="Limpiar", width=6, command=self.main_clear_string)
        self.btn_main_clear.pack(side=tk.LEFT, padx=2)

        self.btn_expand_str = ttk.Button(str_btn_frame, text="🔍 Expandir", command=self.open_expanded_editor)
        self.btn_expand_str.pack(side=tk.LEFT, padx=2)

        self.btn_revert_str = ttk.Button(str_btn_frame, text="⏪ REVERTIR", style='Revert.TButton', command=self.revert_string_direct, state=tk.DISABLED)
        self.btn_revert_str.pack(side=tk.RIGHT, padx=2)

        self.btn_edit_str = ttk.Button(str_btn_frame, text="💾 EDITAR STRING", style='StringEdit.TButton', command=self.apply_string_change, state=tk.DISABLED)
        self.btn_edit_str.pack(side=tk.RIGHT, padx=2)
        
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

    # ----------------------------------------------------
    # GESTIÓN DINÁMICA DE APERTURA / CIERRE
    # ----------------------------------------------------
    def handle_binary_button(self):
        if self.bin_path:
            confirm = messagebox.askyesno("Cerrar Archivo", "¿Desea cerrar el archivo binario y el descriptor actuales?")
            if confirm: self.close_binary_file()
        else:
            self.open_binary_file()

    def close_binary_file(self):
        self.bin_path = None
        self.txt_path = None
        self.history_json_path = None
        self.txt_data.clear()
        self.history_log.clear()
        self.pending_string_reversion.clear()
        self.selected_sec1_item = None
        self.selected_sec2_item = None
        self.current_pointer_offsets.clear()
        
        for row in self.tree_sec1.get_children(): self.tree_sec1.delete(row)
        for row in self.tree_sec2.get_children(): self.tree_sec2.delete(row)
        
        self.lbl_bin_status.configure(text="Ningún archivo binario cargado")
        self.btn_open_bin.configure(text="📁 ABRIR ARCHIVO")
        self.str_entry_var.set("")
        self.copied_ptr_sec1_var.set("-")
        self.copied_offset_var.set("")
        self.ptr_offsets_listbox.delete(0, tk.END)
        self.lbl_str_offset.configure(text="Offset Str: -")
        self.lbl_str_len_info.configure(text="Bytes: 0 / 0")
        self.btn_revert.configure(state=tk.DISABLED)
        self.btn_revert_str.configure(state=tk.DISABLED)
        self.btn_edit_str.configure(state=tk.DISABLED)
        self.update_pointer_flow_label()
        messagebox.showinfo("Cerrado", "El archivo binario y su entorno han sido cerrados correctamente.")

    def handle_table_button(self):
        if self.table_path:
            confirm = messagebox.askyesno("Cerrar Tabla", "¿Desea cerrar la tabla de caracteres actual?")
            if confirm: self.close_table_file()
        else:
            self.open_table_file()

    def close_table_file(self):
        self.table_path = None
        self.char_table.clear()
        self.inverse_table.clear()
        self.lbl_table_status.configure(text="Tabla: NO cargada", foreground='#c53030')
        self.btn_open_table.configure(text="📋 ABRIR TABLA")
        if self.selected_sec2_item: self.load_item_into_editors(self.selected_sec2_item)
        messagebox.showinfo("Cerrado", "La tabla de caracteres ha sido cerrada.")

    # ----------------------------------------------------
    # VENTANA DE HERRAMIENTAS (TAB INTERFACE CORREGIDA)
    # ----------------------------------------------------
    def open_tools_window(self):
        tools_win = tk.Toplevel(self.root)
        tools_win.title("Herramientas de ROM Hacking")
        tools_win.geometry("520x420")
        tools_win.resizable(False, False)
        tools_win.transient(self.root)
        tools_win.grab_set()

        notebook = ttk.Notebook(tools_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Pestaña 1: Tabla (Con la corrección exacta de un solo carácter por lado y altura ajustada)
        tab_tabla = ttk.Frame(notebook, padding="6")
        notebook.add(tab_tabla, text=" Tabla ")

        ttk.Label(tab_tabla, text="Ingrese caracteres seguidos (ej. ty):", font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, pady=2)
        
        pair_entry_var = tk.StringVar()
        entry_pair = ttk.Entry(tab_tabla, textvariable=pair_entry_var, font=('Consolas', 10))
        entry_pair.pack(fill=tk.X, pady=2)

        ttk.Label(tab_tabla, text="Resultado formateado (t=y):", font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, pady=(6, 2))
        
        # Cuadro de texto con altura controlada para dejar espacio a los botones de abajo
        text_frame = ttk.Frame(tab_tabla)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        table_text_widget = tk.Text(text_frame, wrap="word", font=('Consolas', 10), undo=True, height=10)
        table_text_widget.grid(row=0, column=0, sticky="nsew")
        table_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=table_text_widget.yview)
        table_scrollbar.grid(row=0, column=1, sticky="ns")
        table_text_widget.configure(yscrollcommand=table_scrollbar.set)

        def on_pair_typed(*args):
            val = pair_entry_var.get()
            if len(val) >= 2:
                # Lógica corregida: 1 carácter = 1 carácter (ej: t=y)
                formatted_lines = []
                i = 0
                while i < len(val) - 1:
                    c1 = val[i]
                    c2 = val[i+1]
                    formatted_lines.append(f"{c1}={c2}\n")
                    i += 2
                table_text_widget.insert(tk.END, "".join(formatted_lines))
                pair_entry_var.set("")

        pair_entry_var.trace_add("write", on_pair_typed)

        # Botones inferiores Abri y Guardar visibles y ordenados
        tools_btn_frame = ttk.Frame(tab_tabla, padding=(0, 6, 0, 0))
        tools_btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def tools_abrir():
            file_path = filedialog.askopenfilename(title="Abrir Archivo de Tabla", filetypes=[("Archivos de Texto", "*.txt")])
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
                    table_text_widget.delete("1.0", tk.END)
                    table_text_widget.insert("1.0", content)
                except Exception as e: messagebox.showerror("Error", str(e))

        def tools_guardar():
            file_path = filedialog.asksaveasfilename(title="Guardar Archivo de Tabla", defaultextension=".txt", filetypes=[("Archivos de Texto", "*.txt")])
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f: f.write(table_text_widget.get("1.0", "end-1c"))
                    messagebox.showinfo("Éxito", "Tabla guardada correctamente.")
                except Exception as e: messagebox.showerror("Error", str(e))

        ttk.Button(tools_btn_frame, text="📁 Abrir", command=tools_abrir).pack(side=tk.LEFT, padx=3)
        ttk.Button(tools_btn_frame, text="💾 Guardar", command=tools_guardar).pack(side=tk.LEFT, padx=3)

        # Pestaña 2: Limpiador
        tab_limpiador = ttk.Frame(notebook, padding="6")
        notebook.add(tab_limpiador, text=" Limpiador ")
        ttk.Label(tab_limpiador, text="Módulo en desarrollo (Pendiente de implementar).", font=('Segoe UI', 10, 'italic'), foreground='#718096').pack(expand=True)

    # ----------------------------------------------------
    # EVENTOS DE TEXTO
    # ----------------------------------------------------
    def on_main_entry_enter(self, event):
        if self.entry_string.selection_present(): self.entry_string.delete(tk.SEL_FIRST, tk.SEL_LAST)
        pos = self.entry_string.index(tk.INSERT)
        self.entry_string.insert(pos, "\\n")
        return "break"

    def on_main_entry_backspace(self, event):
        if self.entry_string.selection_present(): return None
        pos = self.entry_string.index(tk.INSERT)
        if pos >= 2:
            txt = self.entry_string.get()
            if txt[pos-2:pos] == "\\n":
                self.entry_string.delete(pos - 2, pos)
                return "break"
        return None

    def on_main_entry_delete(self, event):
        if self.entry_string.selection_present(): return None
        pos = self.entry_string.index(tk.INSERT)
        txt = self.entry_string.get()
        if pos <= len(txt) - 2 and txt[pos:pos+2] == "\\n":
            self.entry_string.delete(pos, pos + 2)
            return "break"
        return None

    def main_copy_string(self):
        try:
            if self.entry_string.selection_present(): sel = self.entry_string.selection_get()
            else: sel = self.str_entry_var.get()
        except tk.TclError: sel = self.str_entry_var.get()
        if sel:
            self.root.clipboard_clear()
            self.root.clipboard_append(sel)
            self.root.update()

    def main_paste_string(self):
        try: clip = self.root.clipboard_get()
        except tk.TclError: clip = ""
        if clip:
            escaped_clip = self.to_escaped_nl(clip)
            self.str_entry_var.set(escaped_clip)

    def main_clear_string(self):
        self.str_entry_var.set("")

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
        chk_mod_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(search_control_frame, text="Offset", variable=chk_offset_var).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(search_control_frame, text="Longitud", variable=chk_len_var).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(search_control_frame, text="Puntero", variable=chk_ptr_var).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(search_control_frame, text="String", variable=chk_str_var).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(search_control_frame, text="Mod", variable=chk_mod_var).pack(side=tk.LEFT, padx=2)
        
        search_context = {
            'var': search_var, 'offset': chk_offset_var, 'length': chk_len_var, 
            'pointer': chk_ptr_var, 'string': chk_str_var, 'modified': chk_mod_var
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

    def open_expanded_editor(self):
        if self.expanded_window and self.expanded_window.winfo_exists():
            self.expanded_window.lift()
            return

        top = tk.Toplevel(self.root)
        top.title("Editor Expandido de String")
        top.geometry("580x320")
        top.transient(self.root)
        try: top.attributes('-toolwindow', True)
        except Exception: pass
        self.expanded_window = top

        frame = ttk.Frame(top, padding="8")
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        info_bar = ttk.Frame(frame)
        info_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ttk.Label(info_bar, text="Edición Multilínea (Latin-1 / 0x0A)", font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT)
        self.exp_counter_lbl = ttk.Label(info_bar, text="Chars: 0 | Bytes: 0 / 0", font=('Consolas', 9))
        self.exp_counter_lbl.pack(side=tk.RIGHT)

        txt_frame = ttk.Frame(frame)
        txt_frame.grid(row=1, column=0, sticky="nsew")
        txt_frame.columnconfigure(0, weight=1)
        txt_frame.rowconfigure(0, weight=1)

        exp_text = tk.Text(txt_frame, wrap="word", undo=True, font=('Consolas', 11), padx=8, pady=8)
        exp_text.grid(row=0, column=0, sticky="nsew")
        exp_scrollbar = ttk.Scrollbar(txt_frame, orient="vertical", command=exp_text.yview)
        exp_scrollbar.grid(row=0, column=1, sticky="ns")
        exp_text.configure(yscrollcommand=exp_scrollbar.set)
        self.expanded_text_widget = exp_text

        current_escaped = self.str_entry_var.get()
        exp_text.insert("1.0", self.to_real_nl(current_escaped))

        def on_exp_modified(event=None):
            if self._syncing_editors: return
            self._syncing_editors = True
            try:
                raw_multilinea = exp_text.get("1.0", "end-1c")
                escaped_for_main = self.to_escaped_nl(raw_multilinea)
                if self.str_entry_var.get() != escaped_for_main:
                    self.str_entry_var.set(escaped_for_main)
                self.validate_string_length()
            finally:
                self._syncing_editors = False

        exp_text.bind("<KeyRelease>", on_exp_modified)
        self.validate_string_length()

        btn_frame = ttk.Frame(frame, padding=(0, 8, 0, 0))
        btn_frame.grid(row=2, column=0, sticky="ew")

        def exp_copiar():
            try: sel = exp_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError: sel = exp_text.get("1.0", "end-1c")
            if sel:
                top.clipboard_clear()
                top.clipboard_append(sel)
                top.update()

        def exp_pegar():
            try: clip = top.clipboard_get()
            except tk.TclError: clip = ""
            if clip:
                exp_text.delete("1.0", tk.END)
                exp_text.insert("1.0", self.to_real_nl(clip))
                on_exp_modified()

        def exp_limpiar():
            exp_text.delete("1.0", tk.END)
            on_exp_modified()

        ttk.Button(btn_frame, text="Copiar", command=exp_copiar).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Pegar", command=exp_pegar).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Limpiar", command=exp_limpiar).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Cerrar", command=top.destroy).pack(side=tk.RIGHT, padx=3)

        def on_close():
            self.expanded_text_widget = None
            self.expanded_window = None
            top.destroy()
        top.protocol("WM_DELETE_WINDOW", on_close)

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

        confirm = messagebox.askyesno(
            "Invertir Punteros", 
            f"¿Desea invertir estos punteros directamente en el binario?\n\n"
            f"• Fila {item1['id']} ({item1['offset']}): {ptr1} ➔ {ptr2}\n"
            f"• Fila {item2['id']} ({item2['offset']}): {ptr2} ➔ {ptr1}"
        )

        if not confirm: return

        try:
            bytes_ptr1 = bytes.fromhex(ptr1)
            bytes_ptr2 = bytes.fromhex(ptr2)

            with open(self.bin_path, 'rb') as rb: content = rb.read()

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

            with open(self.bin_path, 'r+b') as wb:
                for off in offsets_p1: wb.seek(off); wb.write(bytes_ptr2)
                for off in offsets_p2: wb.seek(off); wb.write(bytes_ptr1)

            item1['pointer'] = ptr2
            item2['pointer'] = ptr1

            updated_txt_lines = []
            with open(self.txt_path, 'r', encoding='latin-1', errors='replace') as r_txt:
                for line in r_txt:
                    parts = line.strip('\r\n').split('\t')
                    if len(parts) >= 4:
                        curr_off = parts[0].strip().lower()
                        if curr_off == item1['offset'].strip().lower(): parts[2] = ptr2
                        elif curr_off == item2['offset'].strip().lower(): parts[2] = ptr1
                        updated_txt_lines.append("\t".join(parts) + "\n")
                    else: updated_txt_lines.append(line)

            with open(self.txt_path, 'w', encoding='latin-1') as w_txt: w_txt.writelines(updated_txt_lines)

            if self.tree_sec1.exists(id1): self.tree_sec1.item(id1, values=(item1['offset'], item1['length'], item1['pointer'], item1['string']))
            if self.tree_sec2.exists(id1): self.tree_sec2.item(id1, values=(item1['offset'], item1['length'], item1['pointer'], item1['string']))
            if self.tree_sec1.exists(id2): self.tree_sec1.item(id2, values=(item2['offset'], item2['length'], item2['pointer'], item2['string']))
            if self.tree_sec2.exists(id2): self.tree_sec2.item(id2, values=(item2['offset'], item2['length'], item2['pointer'], item2['string']))

            self.copied_ptr_sec1_var.set(item1['pointer'].upper())
            self.scan_binary_for_pointer_matches(item1['pointer'])
            self.update_pointer_flow_label()

            messagebox.showinfo("Éxito", "¡Punteros invertidos y guardados en el binario correctamente!")

        except Exception as e:
            messagebox.showerror("Error", f"Fallo al invertir punteros: {str(e)}")

    def show_about_info(self):
        messagebox.showinfo("Acerca de", "Gestor de punteros V4.4\n==Diseñado por ZARF==\nProgramado con Gemini AI")

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
        self.btn_open_bin.configure(text="❌ CERRAR ARCHIVO")
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
            self.btn_open_table.configure(text="❌ CERRAR TABLA")
            if self.selected_sec2_item: self.load_item_into_editors(self.selected_sec2_item)
        except Exception as e: messagebox.showerror("Error", str(e))

    def parse_descriptor_txt(self):
        self.txt_data.clear()
        try:
            with open(self.txt_path, 'r', encoding='latin-1', errors='replace') as f:
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
        
        if not query and not only_modified:
            self.populate_treeview(tree, self.txt_data)
            return
            
        filtered_results = []
        for item in self.txt_data:
            if only_modified and item['id'] not in self.history_log: continue
            if query:
                match_found = False
                if context['offset'].get() and query in item['offset'].lower(): match_found = True
                if context['length'].get() and query in item['length'].lower(): match_found = True
                if context['pointer'].get() and query in item['pointer'].lower(): match_found = True
                if context['string'].get() and query in item['string'].lower(): match_found = True
                if not match_found: continue
            filtered_results.append(item)
            
        self.populate_treeview(tree, filtered_results)

    def reset_section_view(self, section_num, context):
        context['var'].set("")
        context['modified'].set(False)
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
        try: pointer_bytes = bytes.fromhex(pointer_hex_str.replace(" ", ""))
        except ValueError: return
        try:
            with open(self.bin_path, 'rb') as f: content = f.read()
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
                self.btn_revert_str.configure(state=tk.NORMAL if is_str_modified else tk.DISABLED)
                self.btn_edit_str.configure(state=tk.NORMAL)
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
            decoded_string = clean_buffer.decode('latin-1', errors='replace')
            
            # --- NUEVA LÓGICA DE DETECCIÓN DE PADDING EXACTA CON TU IDEA DEL -2 ---
            with open(self.bin_path, 'rb') as rb:
                # Nos situamos en el offset del string
                start_pos = offset_val
                # Aplicamos el salto restándole 2 a la longitud del descriptor
                jump_pos = start_pos + max(0, max_bytes_to_read - 2)
                rb.seek(jump_pos)
                
                # Leemos un bloque generoso para inspeccionar
                scan_buffer = rb.read(128)
                
                # Omitimos bytes diferentes a 0x00 hasta encontrar el primer 0x00
                idx_scan = 0
                while idx_scan < len(scan_buffer) and scan_buffer[idx_scan] != 0x00:
                    idx_scan += 1
                
                # A partir de ese primer 0x00, contamos cuántos ceros consecutivos hay
                padding_count = 0
                while idx_scan < len(scan_buffer) and scan_buffer[idx_scan] == 0x00:
                    padding_count += 1
                    idx_scan += 1
                    
                self.current_item_padding = padding_count
                
        except Exception:
            decoded_string = self.to_real_nl(item['string'])
            self.current_item_padding = 0

        if self.char_table:
            decoded_string = "".join([self.inverse_table.get(char, char) for char in decoded_string])

        escaped_for_entry = self.to_escaped_nl(decoded_string)

        self.lbl_str_offset.configure(text=f"Offset Str: 0x{item['offset'].upper().replace('0X', '')}")
        self.str_entry_var.set(escaped_for_entry)
        self.validate_string_length()

    def on_main_entry_changed(self, *args):
        self.validate_string_length()
        if self._syncing_editors: return
        if self.expanded_text_widget and self.expanded_window and self.expanded_window.winfo_exists():
            self._syncing_editors = True
            try:
                current_in_exp = self.expanded_text_widget.get("1.0", "end-1c")
                main_real_nl = self.to_real_nl(self.str_entry_var.get())
                if current_in_exp != main_real_nl:
                    self.expanded_text_widget.delete("1.0", tk.END)
                    self.expanded_text_widget.insert("1.0", main_real_nl)
            finally:
                self._syncing_editors = False

    def validate_string_length(self, *args):
        if not self.selected_sec2_item: return
        try:
            max_allowed = int(self.selected_sec2_item['length'])
            escaped_text = self.str_entry_var.get()
            
            real_text = self.to_real_nl(escaped_text)
            mapped_text = "".join([self.char_table.get(c, c) for c in real_text])
            current_len = len(mapped_text.encode('latin-1', errors='replace'))
            
            total_allowed_with_padding = max_allowed + self.current_item_padding
            
            # Cálculo del padding restante dinámico
            if current_len > max_allowed:
                consumed = current_len - max_allowed
                remaining_padding = max(0, self.current_item_padding - consumed)
                padding_str = f" (+{remaining_padding})"
            else:
                padding_str = f" (+{self.current_item_padding})" if self.current_item_padding > 0 else ""

            info_text = f"Bytes: {current_len} / {max_allowed}{padding_str}"
            
            # Si excede el límite total con padding, marcamos error visual y bloqueamos edición
            # Bloquear si ya no hay padding disponible (es decir, si estamos en +0 o excedemos)
            if current_len >= total_allowed_with_padding:
                color = '#c53030'
                self.btn_edit_str.configure(state=tk.DISABLED)
            else:
                color = '#2b6cb0'
                self.btn_edit_str.configure(state=tk.NORMAL)
            
            self.lbl_str_len_info.configure(text=info_text, foreground=color)
            
            if hasattr(self, 'exp_counter_lbl') and self.exp_counter_lbl.winfo_exists():
                chars_len = len(real_text)
                self.exp_counter_lbl.configure(text=f"Chars: {chars_len} | {info_text}", foreground=color)
                
        except ValueError: pass

    # ----------------------------------------------------
    # EDITAR STRING E INYECCIÓN CON PADDING
    # ----------------------------------------------------
    def apply_string_change(self):
        if not self.bin_path or not self.selected_sec2_item:
            messagebox.showwarning("Atención", "Debe seleccionar una línea en la Sección 2 para editar su string.")
            return

        item_sec2 = self.selected_sec2_item
        id_sec2 = item_sec2['id']
        new_string_escaped = self.to_escaped_nl(self.str_entry_var.get())
        
        try:
            max_len = int(item_sec2['length'])
        except ValueError: return

        real_string_for_bin = self.to_real_nl(new_string_escaped)
        mapped_string = "".join([self.char_table.get(c, c) for c in real_string_for_bin])
        encoded_string_bytes = mapped_string.encode('latin-1', errors='replace')
        current_len = len(encoded_string_bytes)

        # Verificación de Padding y advertencia
        is_using_padding = current_len > max_len
        if is_using_padding:
            confirm_pad = messagebox.askyesno(
                "Advertencia de Padding", 
                "El string sobrepasa el límite pero se aprovecha el padding, sin embargo puede causar conflictos\n¿Está seguro?"
            )
            if not confirm_pad: return
            padding_bytes_used = current_len - max_len
        else:
            padding_bytes_used = 0

        total_alloc = max_len + padding_bytes_used
        final_string_buffer = encoded_string_bytes + (b'\x00' * (total_alloc - current_len))
        target_string_offset = int(item_sec2['offset'], 16)

        try:
            if id_sec2 not in self.history_log: 
                self.history_log[id_sec2] = {}
            if 'old_string_bytes' not in self.history_log[id_sec2]:
                with open(self.bin_path, 'rb') as rb:
                    rb.seek(target_string_offset)
                    # Leemos el bloque original abarcando también el padding para poder restaurarlo perfecto
                    original_str_bytes = rb.read(total_alloc)
                self.history_log[id_sec2]['old_string_bytes'] = original_str_bytes.hex()
                self.history_log[id_sec2]['string_offset_used'] = target_string_offset
                
                # Formato solicitado para string_length_used con +# si usa padding (ej: 316+3)
                if is_using_padding:
                    self.history_log[id_sec2]['string_length_used'] = f"{max_len}+{padding_bytes_used}"
                else:
                    self.history_log[id_sec2]['string_length_used'] = max_len
                    
                self.history_log[id_sec2]['original_descriptor_text'] = self.to_escaped_nl(item_sec2['string'])

            self.save_history_to_disk()

            # Escribir en el binario
            with open(self.bin_path, 'r+b') as wb:
                wb.seek(target_string_offset)
                wb.write(final_string_buffer)

            # Actualizar archivo descriptor .txt
            updated_txt_lines = []
            with open(self.txt_path, 'r', encoding='latin-1', errors='replace') as r_txt:
                for line in r_txt:
                    parts = line.strip('\r\n').split('\t')
                    if len(parts) >= 4:
                        curr_off = parts[0].strip().lower()
                        if curr_off == item_sec2['offset'].strip().lower():
                            parts[3] = new_string_escaped
                        updated_txt_lines.append("\t".join(parts) + "\n")
                    else: updated_txt_lines.append(line)
                        
            with open(self.txt_path, 'w', encoding='latin-1') as w_txt: 
                w_txt.writelines(updated_txt_lines)

            messagebox.showinfo("Éxito", "¡String editado e inyectado correctamente!")
            
            item_sec2['string'] = new_string_escaped
            
            if self.tree_sec2.exists(id_sec2):
                self.tree_sec2.item(id_sec2, values=(item_sec2['offset'], item_sec2['length'], item_sec2['pointer'], item_sec2['string']))
            if self.tree_sec1.exists(id_sec2):
                self.tree_sec1.item(id_sec2, values=(item_sec2['offset'], item_sec2['length'], item_sec2['pointer'], item_sec2['string']))

            self.on_select_section2(None)

        except Exception as e:
            messagebox.showerror("Error", f"Fallo al inyectar el string: {str(e)}")

    def revert_string_direct(self):
        """Reversión directa del string con mensaje de confirmación sin requerir edición previa."""
        if not self.selected_sec2_item: return
        item_id = self.selected_sec2_item['id']
        if item_id not in self.history_log or 'old_string_bytes' not in self.history_log[item_id]: return

        confirm = messagebox.askyesno(
            "Revertir String", 
            "¿Restaurar String original?\nEl string editado se perderá"
        )
        if not confirm: return

        hist = self.history_log[item_id]
        original_bytes = bytes.fromhex(hist['old_string_bytes'])
        target_offset = hist['string_offset_used']
        original_text = hist['original_descriptor_text']

        try:
            # Restaurar bytes en el binario
            with open(self.bin_path, 'r+b') as wb:
                wb.seek(target_offset)
                wb.write(original_bytes)

            # Restaurar en el archivo .txt descriptor
            updated_txt_lines = []
            with open(self.txt_path, 'r', encoding='latin-1', errors='replace') as r_txt:
                for line in r_txt:
                    parts = line.strip('\r\n').split('\t')
                    if len(parts) >= 4:
                        curr_off = parts[0].strip().lower()
                        if curr_off == self.selected_sec2_item['offset'].strip().lower():
                            parts[3] = original_text
                        updated_txt_lines.append("\t".join(parts) + "\n")
                    else: updated_txt_lines.append(line)

            with open(self.txt_path, 'w', encoding='latin-1') as w_txt:
                w_txt.writelines(updated_txt_lines)

            # Limpiar del historial de string
            del self.history_log[item_id]['old_string_bytes']
            del self.history_log[item_id]['string_offset_used']
            del self.history_log[item_id]['string_length_used']
            del self.history_log[item_id]['original_descriptor_text']
            if not self.history_log[item_id]: del self.history_log[item_id]
            self.save_history_to_disk()

            # Actualizar memoria y UI
            self.selected_sec2_item['string'] = original_text
            self.load_item_into_editors(self.selected_sec2_item)
            
            if self.tree_sec2.exists(item_id):
                self.tree_sec2.item(item_id, values=(self.selected_sec2_item['offset'], self.selected_sec2_item['length'], self.selected_sec2_item['pointer'], original_text))
            if self.tree_sec1.exists(item_id):
                self.tree_sec1.item(item_id, values=(self.selected_sec2_item['offset'], self.selected_sec2_item['length'], self.selected_sec2_item['pointer'], original_text))

            self.btn_revert_str.configure(state=tk.DISABLED)
            messagebox.showinfo("Éxito", "String restaurado a sus valores originales de fábrica.")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo revertir el string: {str(e)}")

    def apply_changes(self):
        """Función exclusiva para CAMBIAR PTR (Punteros)."""
        if not self.bin_path or not self.selected_sec1_item:
            messagebox.showwarning("Atención", "Debe seleccionar un origen en la Sección 1 y un archivo binario cargado.")
            return

        id_sec1 = self.selected_sec1_item['id']
        item_sec1 = self.selected_sec1_item
        current_descriptor_ptr = item_sec1['pointer'].strip().replace(" ", "").upper()

        if self.chk_manual_var.get():
            new_pointer_hex = self.manual_ptr_var.get().strip().replace(" ", "").upper()
            if not new_pointer_hex: 
                messagebox.showerror("Error", "Puntero manual vacío.")
                return
        else:
            if not self.selected_sec2_item: 
                messagebox.showwarning("Atención", "Seleccione una fila destino en la Sección 2.")
                return
            new_pointer_hex = self.selected_sec2_item['pointer'].strip().replace(" ", "").upper()

        is_ptr_changing = (current_descriptor_ptr != new_pointer_hex)
        if not is_ptr_changing:
            messagebox.showinfo("Aviso", "El puntero de origen y el de destino son idénticos.")
            return

        if id_sec1 in self.history_log and 'old_pointer' in self.history_log[id_sec1]:
            if current_descriptor_ptr != self.history_log[id_sec1]['old_pointer'].upper():
                messagebox.showerror("Seguridad", "Este puntero ya fue modificado.\nDebe presionar 'REVERTIR PTR' para poder cambiarlo de nuevo.")
                return

        if not re.match(r"^[0-9a-fA-F]+$", new_pointer_hex) or len(new_pointer_hex) % 2 != 0:
            messagebox.showerror("Error", "Puntero hexadecimal inválido.")
            return

        offsets_to_write = []
        if self.chk_all_offsets_var.get():
            offsets_to_write = list(self.current_pointer_offsets)
            if not offsets_to_write: 
                messagebox.showerror("Error", "No hay offsets válidos para aplicar a todos.")
                return
        else:
            selected_idx = self.ptr_offsets_listbox.curselection()
            if not selected_idx or self.current_left_view == 1:
                messagebox.showerror("Error", "Seleccione un offset válido en la listbox (Vista ACTUAL).")
                return
            offsets_to_write.append(self.current_pointer_offsets[selected_idx[0]])

        try:
            if id_sec1 not in self.history_log: self.history_log[id_sec1] = {}
            if 'old_pointer' not in self.history_log[id_sec1]:
                self.history_log[id_sec1]['old_pointer'] = current_descriptor_ptr
                self.history_log[id_sec1]['offsets'] = list(self.current_pointer_offsets)
            self.history_log[id_sec1]['offsets_written_history'] = list(offsets_to_write)

            self.save_history_to_disk()

            with open(self.bin_path, 'r+b') as wb:
                for off in offsets_to_write:
                    wb.seek(off)
                    wb.write(bytes.fromhex(new_pointer_hex))
                
            updated_txt_lines = []
            with open(self.txt_path, 'r', encoding='latin-1', errors='replace') as r_txt:
                for line in r_txt:
                    parts = line.strip('\r\n').split('\t')
                    if len(parts) >= 4:
                        curr_off = parts[0].strip().lower()
                        if curr_off == item_sec1['offset'].strip().lower():
                            parts[2] = new_pointer_hex.upper()
                        updated_txt_lines.append("\t".join(parts) + "\n")
                    else: updated_txt_lines.append(line)
                        
            with open(self.txt_path, 'w', encoding='latin-1') as w_txt: 
                w_txt.writelines(updated_txt_lines)

            messagebox.showinfo("Éxito", "¡Punteros cambiados y guardados con éxito!")
            self.chk_all_offsets_var.set(False)
            
            item_sec1['pointer'] = new_pointer_hex.upper()
            
            if self.tree_sec1.exists(id_sec1):
                self.tree_sec1.item(id_sec1, values=(item_sec1['offset'], item_sec1['length'], item_sec1['pointer'], item_sec1['string']))
            if self.tree_sec2.exists(id_sec1):
                self.tree_sec2.item(id_sec1, values=(item_sec1['offset'], item_sec1['length'], item_sec1['pointer'], item_sec1['string']))

            self.scan_binary_for_pointer_matches(item_sec1['pointer'])
            self.on_select_section1(None)
            
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al cambiar punteros: {str(e)}")

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
                with open(self.txt_path, 'r', encoding='latin-1', errors='replace') as r_txt:
                    for line in r_txt:
                        parts = line.strip('\r\n').split('\t')
                        if len(parts) >= 4 and parts[0].strip().lower() == self.selected_sec1_item['offset'].strip().lower():
                            parts[2] = target_pointer.upper()
                            updated_txt_lines.append("\t".join(parts) + "\n")
                        else: updated_txt_lines.append(line)
                with open(self.txt_path, 'w', encoding='latin-1') as w_txt: w_txt.writelines(updated_txt_lines)
                
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
