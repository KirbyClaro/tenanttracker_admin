import customtkinter as ctk
import tkinter.ttk as ttk
import tkinter as tk
import time
import sqlite3
from database import init_db
from tkcalendar import DateEntry

# Initialize database on launch
init_db()

class TenantTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("TenantTracker Admin")
        self.geometry("1200x750")
        
        self.tabview = ctk.CTkTabview(self, width=1150, height=700)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.tab_tenants = self.tabview.add("Tenant Information")
        self.tab_financials = self.tabview.add("Financials")
        self.tab_settings = self.tabview.add("Settings")

        self.form_visible = False
        self.editing_tenant_id = None

        self.setup_tenant_tab()

    def setup_tenant_tab(self):
        # --- HEADER ---
        self.header_frame = ctk.CTkFrame(self.tab_tenants, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=10)

        self.title_label = ctk.CTkLabel(self.header_frame, text="Tenant Management", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left")

        self.toggle_btn = ctk.CTkButton(self.header_frame, text="+ Add New Tenant", command=self.toggle_form, fg_color="#1f538d", hover_color="#14375e")
        self.toggle_btn.pack(side="left", padx=20)

        self.clock_label = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=14))
        self.clock_label.pack(side="right")
        self.update_clock()

        # --- SEARCH & FILTER BAR ---
        self.search_frame = ctk.CTkFrame(self.tab_tenants, fg_color="#2b2b2b")
        self.search_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.filter_var = ctk.StringVar(value="Active")
        self.status_filter = ctk.CTkOptionMenu(
            self.search_frame, values=["Active", "Archived", "All"], 
            variable=self.filter_var, command=self.trigger_search, width=120
        )
        self.status_filter.pack(side="left", padx=10, pady=10)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.trigger_search)
        self.search_entry = ctk.CTkEntry(
            self.search_frame, placeholder_text="Search by Name or Room...", 
            textvariable=self.search_var, width=300
        )
        self.search_entry.pack(side="left", padx=(0, 10), pady=10)

        self.reset_cols_btn = ctk.CTkButton(
            self.search_frame, text="Reset Columns", command=self.reset_table_columns, 
            width=120, fg_color="#565b5e", hover_color="#343638"
        )
        self.reset_cols_btn.pack(side="right", padx=10, pady=10)

        # --- CONTENT LAYOUT ---
        self.tenant_content = ctk.CTkFrame(self.tab_tenants, fg_color="transparent")
        self.tenant_content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Left: Scrollable Input Form
        self.form_frame = ctk.CTkScrollableFrame(self.tenant_content, width=350, label_text="Tenant Details")

        self.contact_var = ctk.StringVar()
        self.contact_var.trace_add("write", self.validate_contact)
        
        self.monthly_var = ctk.StringVar()
        self.monthly_var.trace_add("write", self.validate_monthly)

        self.due_day_var = ctk.StringVar()
        self.due_day_var.trace_add("write", self.validate_due_day)

        self.entries = {}
        
        self.fields = [
            "Status", "Full Name", "Address", "Room Number", "Date Started",
            "Lease Term", "Move Out Date", "Monthly Due", "Rent Due Day", "Valid ID", "Working/Job",
            "Messenger Link", "Email", "Contact Number"
        ]

        for field in self.fields:
            lbl = ctk.CTkLabel(self.form_frame, text=field)
            lbl.pack(anchor="w", padx=10, pady=(5, 0))

            if field in ["Date Started", "Move Out Date"]:
                ent = DateEntry(self.form_frame, width=45, font=('Segoe UI', 11), background='#1f538d', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
                ent.pack(padx=10, pady=(0, 5), ipady=4)
                self.entries[field] = ent
            elif field == "Status":
                ent = ctk.CTkOptionMenu(self.form_frame, values=["Active", "Archived"], width=300)
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent
            elif field == "Contact Number":
                ent = ctk.CTkEntry(self.form_frame, width=300, textvariable=self.contact_var)
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent
            elif field == "Monthly Due":
                ent = ctk.CTkEntry(self.form_frame, width=300, textvariable=self.monthly_var)
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent
            elif field == "Rent Due Day":
                ent = ctk.CTkEntry(self.form_frame, width=300, textvariable=self.due_day_var, placeholder_text="e.g., 5 or 15")
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent
            else:
                ent = ctk.CTkEntry(self.form_frame, width=300)
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent

        lbl_notes = ctk.CTkLabel(self.form_frame, text="Remarks / Notes")
        lbl_notes.pack(anchor="w", padx=10, pady=(5, 0))
        self.notes_box = ctk.CTkTextbox(self.form_frame, width=300, height=80)
        self.notes_box.pack(padx=10, pady=(0, 5))

        self.check_vars = {
            "Agreement Signed": ctk.IntVar(),
            "Advance Paid": ctk.IntVar(),
            "Deposit Paid": ctk.IntVar()
        }

        for check_name, var in self.check_vars.items():
            chk = ctk.CTkCheckBox(self.form_frame, text=check_name, variable=var)
            chk.pack(anchor="w", padx=10, pady=5)

        self.save_btn = ctk.CTkButton(self.form_frame, text="Save Tenant", command=self.save_tenant_to_db, fg_color="green", hover_color="darkgreen")
        self.save_btn.pack(pady=20, padx=10, fill="x")

        # Right: Display Table Area
        self.table_frame = ctk.CTkFrame(self.tenant_content)
        self.table_frame.pack(side="right", fill="both", expand=True)
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=40, font=('Segoe UI', 11), fieldbackground="#2b2b2b", bordercolor="#343638", borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", font=('Segoe UI', 12, 'bold'), relief="flat")
        style.map("Treeview.Heading", background=[('active', '#343638')])

        self.columns = (
            "ID", "Status", "Name", "Address", "Room", "Started", "Term", 
            "Move Out", "Monthly", "Due Day", "Valid ID", "Job", "Messenger", 
            "Email", "Contact", "Notes", "Agreement", "Advance", "Deposit", "Last Edited"
        )
        self.tenant_table = ttk.Treeview(self.table_frame, columns=self.columns, show="headings")
        
        self.tree_scroll_y = ctk.CTkScrollbar(self.table_frame, orientation="vertical", command=self.tenant_table.yview)
        self.tree_scroll_y.pack(side="right", fill="y", pady=(10, 0))

        self.tree_scroll_x = ctk.CTkScrollbar(self.table_frame, orientation="horizontal", command=self.tenant_table.xview)
        self.tree_scroll_x.pack(side="bottom", fill="x", padx=(10, 0))

        self.tenant_table.configure(yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set)
        
        for col in self.columns:
            self.tenant_table.heading(col, text=col)
            
        self.reset_table_columns()
        self.tenant_table.pack(fill="both", expand=True, padx=(10, 0), pady=(10, 0))

        # --- CONTEXT MENU FOR COPYING DATA ---
        self.context_menu = tk.Menu(self, tearoff=0, bg="#343638", fg="white", activebackground="#1f538d")
        self.context_menu.add_command(label="Copy Cell Value", command=self.copy_cell)
        
        self.tenant_table.bind("<Button-3>", self.show_context_menu)

        # --- ACTION BUTTONS ---
        self.action_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=10, pady=(10, 0))

        # New View Button
        self.view_btn = ctk.CTkButton(self.action_frame, text="View Selected", command=self.view_tenant_details, fg_color="#1f538d", hover_color="#14375e")
        self.view_btn.pack(side="left", padx=(0, 10))

        self.edit_btn = ctk.CTkButton(self.action_frame, text="Edit Selected", command=self.load_for_editing, fg_color="#B8860B", hover_color="#8B6508")
        self.edit_btn.pack(side="left", padx=(0, 10))

        self.delete_btn = ctk.CTkButton(self.action_frame, text="Delete Selected", command=self.delete_tenant, fg_color="#8B0000", hover_color="#660000")
        self.delete_btn.pack(side="left")

        self.load_tenants_from_db()

    def view_tenant_details(self):
        selected_item = self.tenant_table.selection()
        if not selected_item: 
            return # Do nothing if no row is selected
            
        item_values = self.tenant_table.item(selected_item[0])['values']
        tenant_name = str(item_values[2])
        
        # Create the pop-up window
        view_win = ctk.CTkToplevel(self)
        view_win.title(f"Tenant Card: {tenant_name}")
        view_win.geometry("500x700")
        view_win.attributes("-topmost", True) # Keep window on top so it doesn't get lost
        
        # Header Label
        header = ctk.CTkLabel(view_win, text=f"Data for: {tenant_name}", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=(20, 10))
        
        # Scrollable container for the data
        scroll_frame = ctk.CTkScrollableFrame(view_win, width=450, height=550)
        scroll_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        # Iterate through the columns and display them
        for idx, col_name in enumerate(self.columns):
            val = item_values[idx]
            display_val = str(val) if val != "None" and val != "" else "N/A"
            
            if col_name == "Notes":
                # Special handling for Notes: Give it a read-only text box
                lbl_title = ctk.CTkLabel(scroll_frame, text=f"{col_name}:", font=ctk.CTkFont(weight="bold"))
                lbl_title.pack(anchor="w", pady=(15, 0), padx=5)
                
                textbox = ctk.CTkTextbox(scroll_frame, width=420, height=100)
                textbox.pack(anchor="w", pady=(0, 10), padx=5)
                textbox.insert("1.0", display_val)
                textbox.configure(state="disabled") # Prevents typing
            else:
                # Standard row design for other details
                row_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=4, padx=5)
                
                lbl_title = ctk.CTkLabel(row_frame, text=f"{col_name}:", font=ctk.CTkFont(weight="bold"), width=120, anchor="w")
                lbl_title.pack(side="left")
                
                # wraplength allows long text like addresses to break to a new line
                lbl_val = ctk.CTkLabel(row_frame, text=display_val, anchor="w", wraplength=280, justify="left")
                lbl_val.pack(side="left", fill="x", expand=True)
        
        # Close Button at the bottom
        close_btn = ctk.CTkButton(view_win, text="Close Window", command=view_win.destroy, fg_color="#565b5e", hover_color="#343638")
        close_btn.pack(pady=(10, 20))

    def show_context_menu(self, event):
        region = self.tenant_table.identify_region(event.x, event.y)
        if region == "cell":
            self.right_click_row = self.tenant_table.identify_row(event.y)
            self.right_click_col = self.tenant_table.identify_column(event.x)
            self.tenant_table.selection_set(self.right_click_row)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def copy_cell(self):
        if hasattr(self, 'right_click_row') and hasattr(self, 'right_click_col'):
            col_index = int(self.right_click_col.replace('#', '')) - 1
            item_values = self.tenant_table.item(self.right_click_row)['values']
            
            if 0 <= col_index < len(item_values):
                cell_value = str(item_values[col_index])
                self.clipboard_clear()
                self.clipboard_append(cell_value)
                self.update() 
                
                original_title = "TenantTracker Admin"
                self.title("TenantTracker Admin - Copied to Clipboard!")
                self.after(1500, lambda: self.title(original_title))

    def reset_table_columns(self):
        column_widths = {
            "ID": 40, "Status": 80, "Name": 180, "Address": 280, "Room": 60, 
            "Started": 100, "Term": 80, "Move Out": 100, "Monthly": 90, "Due Day": 80,
            "Valid ID": 130, "Job": 140, "Messenger": 180, "Email": 220, 
            "Contact": 120, "Notes": 250, "Agreement": 80, "Advance": 80, 
            "Deposit": 80, "Last Edited": 170
        }
        
        for col, width in column_widths.items():
            anchor_val = "w" if col in ["Name", "Address", "Messenger", "Email", "Notes", "Job", "Valid ID"] else "center"
            self.tenant_table.column(col, width=width, anchor=anchor_val)

    def toggle_form(self):
        if self.form_visible:
            self.form_frame.pack_forget()
            self.toggle_btn.configure(text="+ Add New Tenant", fg_color="#1f538d", hover_color="#14375e")
            self.form_visible = False
            if self.editing_tenant_id:
                self.clear_form()
        else:
            self.form_frame.pack(side="left", fill="y", padx=(0, 10), before=self.table_frame)
            self.toggle_btn.configure(text="- Close Form", fg_color="#8B0000", hover_color="#660000")
            self.form_visible = True

    def validate_contact(self, *args):
        cv = self.contact_var.get()
        no_letters = ''.join(filter(str.isdigit, cv))
        if cv != no_letters: self.contact_var.set(no_letters)

    def validate_monthly(self, *args):
        cv = self.monthly_var.get()
        filtered = ''.join([c for c in cv if c.isdigit() or c == '.'])
        if filtered.count('.') > 1:
            parts = filtered.split('.')
            filtered = parts[0] + '.' + ''.join(parts[1:])
        if cv != filtered: 
            self.monthly_var.set(filtered)

    def validate_due_day(self, *args):
        cv = self.due_day_var.get()
        no_letters = ''.join(filter(str.isdigit, cv))
        if no_letters:
            if int(no_letters) > 31: 
                no_letters = "31"
        if cv != no_letters: 
            self.due_day_var.set(no_letters)

    def trigger_search(self, *args):
        self.load_tenants_from_db()

    def update_clock(self):
        current_time = time.strftime('%I:%M:%S %p | %B %d, %Y')
        self.clock_label.configure(text=current_time)
        self.after(1000, self.update_clock)

    def load_for_editing(self):
        selected_item = self.tenant_table.selection()
        if not selected_item: return
            
        item_values = self.tenant_table.item(selected_item[0])['values']
        
        if not self.form_visible:
            self.toggle_form()

        self.editing_tenant_id = item_values[0]
        self.save_btn.configure(text="Update Tenant", fg_color="#B8860B", hover_color="#8B6508")
        
        for idx, field in enumerate(self.fields):
            val = str(item_values[idx + 1]) if item_values[idx + 1] != "None" else ""
            if field in ["Date Started", "Move Out Date"]:
                self.entries[field].set_date(val)
            elif field == "Status":
                self.entries[field].set(val)
            else:
                self.entries[field].delete(0, 'end')
                self.entries[field].insert(0, val)

        self.notes_box.delete("1.0", "end")
        self.notes_box.insert("1.0", str(item_values[15]) if item_values[15] != "None" else "")

        self.check_vars["Agreement Signed"].set(1 if item_values[16] == "Yes" else 0)
        self.check_vars["Advance Paid"].set(1 if item_values[17] == "Yes" else 0)
        self.check_vars["Deposit Paid"].set(1 if item_values[18] == "Yes" else 0)

    def delete_tenant(self):
        selected_item = self.tenant_table.selection()
        if not selected_item: return
        tenant_id = self.tenant_table.item(selected_item[0])['values'][0]
        
        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
        conn.commit()
        conn.close()
        self.load_tenants_from_db()

    def clear_form(self):
        for field, ent in self.entries.items():
            if field in ["Date Started", "Move Out Date"]:
                ent.set_date(time.strftime('%Y-%m-%d'))
            elif field == "Status":
                ent.set("Active")
            else:
                ent.delete(0, 'end')
                
        self.notes_box.delete("1.0", "end")
        
        for var in self.check_vars.values():
            var.set(0)
            
        self.editing_tenant_id = None
        self.save_btn.configure(text="Save Tenant", fg_color="green", hover_color="darkgreen")

    def save_tenant_to_db(self):
        data = [self.entries[field].get() for field in self.fields]
        data.append(self.notes_box.get("1.0", "end-1c")) 
        data.extend([self.check_vars[check].get() for check in self.check_vars])
        
        current_timestamp = time.strftime('%Y-%m-%d %I:%M %p')
        data.append(current_timestamp)

        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()
        
        if self.editing_tenant_id:
            data.append(self.editing_tenant_id)
            cursor.execute('''
                UPDATE tenants SET
                    status=?, full_name=?, address=?, room_number=?, date_started=?, lease_term=?, move_out_date=?,
                    monthly_due=?, rent_due_day=?, valid_id=?, job=?, messenger_link=?, email=?, contact_number=?, notes=?,
                    agreement_signed=?, advance_paid=?, deposit_paid=?, last_edited=?
                WHERE id=?
            ''', data)
        else:
            cursor.execute('''
                INSERT INTO tenants (
                    status, full_name, address, room_number, date_started, lease_term, move_out_date,
                    monthly_due, rent_due_day, valid_id, job, messenger_link, email, contact_number, notes,
                    agreement_signed, advance_paid, deposit_paid, last_edited
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            
        conn.commit()
        conn.close()

        self.clear_form()
        self.load_tenants_from_db()
        self.toggle_form()

    def load_tenants_from_db(self):
        for item in self.tenant_table.get_children():
            self.tenant_table.delete(item)
            
        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()
        
        status_filter = self.filter_var.get()
        search_text = self.search_var.get()
        
        query = "SELECT * FROM tenants WHERE 1=1"
        params = []
        
        if status_filter != "All":
            query += " AND status = ?"
            params.append(status_filter)
            
        if search_text:
            query += " AND (full_name LIKE ? OR room_number LIKE ?)"
            params.extend([f"%{search_text}%", f"%{search_text}%"])
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        for row in rows:
            formatted_row = list(row)
            formatted_row[16] = "Yes" if formatted_row[16] == 1 else "No" 
            formatted_row[17] = "Yes" if formatted_row[17] == 1 else "No" 
            formatted_row[18] = "Yes" if formatted_row[18] == 1 else "No" 
            
            self.tenant_table.insert("", "end", values=formatted_row)
            
        conn.close()

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = TenantTrackerApp()
    app.mainloop()