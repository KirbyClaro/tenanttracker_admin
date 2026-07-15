import customtkinter as ctk
import tkinter.ttk as ttk
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
        self.geometry("1100x700")
        
        # Setup Main Tabview
        self.tabview = ctk.CTkTabview(self, width=1050, height=650)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        # Create Tabs
        self.tab_tenants = self.tabview.add("Tenant Information")
        self.tab_financials = self.tabview.add("Financials")
        self.tab_settings = self.tabview.add("Settings")

        # Form State
        self.form_visible = False
        self.editing_tenant_id = None  # Tracks if we are editing an existing tenant

        self.setup_tenant_tab()

    def setup_tenant_tab(self):
        # --- HEADER ---
        self.header_frame = ctk.CTkFrame(self.tab_tenants, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=10)

        self.title_label = ctk.CTkLabel(self.header_frame, text="Tenant Management", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left")

        # Toggle Form Button
        self.toggle_btn = ctk.CTkButton(
            self.header_frame, 
            text="+ Add New Tenant", 
            command=self.toggle_form, 
            fg_color="#1f538d", 
            hover_color="#14375e"
        )
        self.toggle_btn.pack(side="left", padx=20)

        self.clock_label = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=14))
        self.clock_label.pack(side="right")
        self.update_clock()

        # --- CONTENT LAYOUT ---
        self.tenant_content = ctk.CTkFrame(self.tab_tenants, fg_color="transparent")
        self.tenant_content.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: Scrollable Input Form
        self.form_frame = ctk.CTkScrollableFrame(self.tenant_content, width=350, label_text="Tenant Details")

        self.contact_var = ctk.StringVar()
        self.contact_var.trace_add("write", self.validate_contact)

        self.entries = {}
        self.fields = [
            "Full Name", "Address", "Room Number", "Date Started",
            "Lease Term", "Move Out Date", "Monthly Due",
            "Valid ID", "Working/Job", "Messenger Link",
            "Email", "Contact Number"
        ]

        for field in self.fields:
            lbl = ctk.CTkLabel(self.form_frame, text=field)
            lbl.pack(anchor="w", padx=10, pady=(5, 0))

            if field in ["Date Started", "Move Out Date"]:
                ent = DateEntry(
                    self.form_frame, width=45, font=('Segoe UI', 11),
                    background='#1f538d', foreground='white', borderwidth=0,
                    headersbackground='#1f538d', headersforeground='white',
                    selectbackground='#14375e', selectforeground='white',
                    fieldbackground='#343638', date_pattern='yyyy-mm-dd'
                )
                ent.pack(padx=10, pady=(0, 5), ipady=4)
                self.entries[field] = ent

            elif field == "Contact Number":
                ent = ctk.CTkEntry(self.form_frame, width=300, textvariable=self.contact_var)
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent

            else:
                ent = ctk.CTkEntry(self.form_frame, width=300)
                ent.pack(padx=10, pady=(0, 5))
                self.entries[field] = ent

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
        style.configure("Treeview", background="#2b2b2b", foreground="white", 
                        rowheight=40, font=('Segoe UI', 12),
                        fieldbackground="#2b2b2b", bordercolor="#343638", borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", 
                        font=('Segoe UI', 13, 'bold'), relief="flat")
        style.map("Treeview.Heading", background=[('active', '#343638')])

        columns = (
            "ID", "Name", "Address", "Room", "Started", "Term", 
            "Move Out", "Monthly", "Valid ID", "Job", "Messenger", 
            "Email", "Contact", "Agreement", "Advance", "Deposit"
        )
        self.tenant_table = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        
        self.tree_scroll_y = ctk.CTkScrollbar(self.table_frame, orientation="vertical", command=self.tenant_table.yview)
        self.tree_scroll_y.pack(side="right", fill="y", pady=(10, 0))

        self.tree_scroll_x = ctk.CTkScrollbar(self.table_frame, orientation="horizontal", command=self.tenant_table.xview)
        self.tree_scroll_x.pack(side="bottom", fill="x", padx=(10, 0))

        self.tenant_table.configure(yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set)
        
        for col in columns:
            self.tenant_table.heading(col, text=col)
            
        self.tenant_table.column("ID", width=50, anchor="center")
        self.tenant_table.column("Name", width=200, anchor="w")
        self.tenant_table.column("Address", width=250, anchor="w")
        self.tenant_table.column("Room", width=80, anchor="center")
        self.tenant_table.column("Started", width=120, anchor="center")
        self.tenant_table.column("Term", width=100, anchor="center")
        self.tenant_table.column("Move Out", width=120, anchor="center")
        self.tenant_table.column("Monthly", width=100, anchor="center")
        self.tenant_table.column("Valid ID", width=150, anchor="w")
        self.tenant_table.column("Job", width=150, anchor="w")
        self.tenant_table.column("Messenger", width=150, anchor="w")
        self.tenant_table.column("Email", width=200, anchor="w")
        self.tenant_table.column("Contact", width=150, anchor="center")
        self.tenant_table.column("Agreement", width=100, anchor="center")
        self.tenant_table.column("Advance", width=100, anchor="center")
        self.tenant_table.column("Deposit", width=100, anchor="center")
        
        self.tenant_table.pack(fill="both", expand=True, padx=(10, 0), pady=(10, 0))

        # --- ACTION BUTTONS (Below the Table) ---
        self.action_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.edit_btn = ctk.CTkButton(self.action_frame, text="Edit Selected", command=self.load_for_editing, fg_color="#B8860B", hover_color="#8B6508")
        self.edit_btn.pack(side="left", padx=(0, 10))

        self.delete_btn = ctk.CTkButton(self.action_frame, text="Delete Selected", command=self.delete_tenant, fg_color="#8B0000", hover_color="#660000")
        self.delete_btn.pack(side="left")

        self.load_tenants_from_db()

    def toggle_form(self):
        if self.form_visible:
            self.form_frame.pack_forget()
            self.toggle_btn.configure(text="+ Add New Tenant", fg_color="#1f538d", hover_color="#14375e")
            self.form_visible = False
            
            # Reset form to blank state if we were editing
            if self.editing_tenant_id:
                self.clear_form()
        else:
            self.form_frame.pack(side="left", fill="y", padx=(0, 10), before=self.table_frame)
            self.toggle_btn.configure(text="- Close Form", fg_color="#8B0000", hover_color="#660000")
            self.form_visible = True

    def validate_contact(self, *args):
        current_value = self.contact_var.get()
        numbers_only = ''.join(filter(str.isdigit, current_value))
        if current_value != numbers_only:
            self.contact_var.set(numbers_only)

    def update_clock(self):
        current_time = time.strftime('%I:%M:%S %p | %B %d, %Y')
        self.clock_label.configure(text=current_time)
        self.after(1000, self.update_clock)

    def load_for_editing(self):
        # Grab the currently selected row
        selected_item = self.tenant_table.selection()
        if not selected_item:
            return  # Nothing is selected
            
        item_values = self.tenant_table.item(selected_item[0])['values']
        
        # Open the form if it is closed
        if not self.form_visible:
            self.toggle_form()

        # Set the editing ID and change button visuals
        self.editing_tenant_id = item_values[0]
        self.save_btn.configure(text="Update Tenant", fg_color="#B8860B", hover_color="#8B6508")
        
        # Populate input fields with the selected data
        # Note: item_values indices map directly to the columns defined in the table
        self.entries["Full Name"].delete(0, 'end')
        self.entries["Full Name"].insert(0, str(item_values[1]) if item_values[1] != "None" else "")
        
        self.entries["Address"].delete(0, 'end')
        self.entries["Address"].insert(0, str(item_values[2]) if item_values[2] != "None" else "")
        
        self.entries["Room Number"].delete(0, 'end')
        self.entries["Room Number"].insert(0, str(item_values[3]) if item_values[3] != "None" else "")
        
        self.entries["Date Started"].set_date(item_values[4])
        
        self.entries["Lease Term"].delete(0, 'end')
        self.entries["Lease Term"].insert(0, str(item_values[5]) if item_values[5] != "None" else "")
        
        self.entries["Move Out Date"].set_date(item_values[6])
        
        self.entries["Monthly Due"].delete(0, 'end')
        self.entries["Monthly Due"].insert(0, str(item_values[7]) if item_values[7] != "None" else "")
        
        self.entries["Valid ID"].delete(0, 'end')
        self.entries["Valid ID"].insert(0, str(item_values[8]) if item_values[8] != "None" else "")
        
        self.entries["Working/Job"].delete(0, 'end')
        self.entries["Working/Job"].insert(0, str(item_values[9]) if item_values[9] != "None" else "")
        
        self.entries["Messenger Link"].delete(0, 'end')
        self.entries["Messenger Link"].insert(0, str(item_values[10]) if item_values[10] != "None" else "")
        
        self.entries["Email"].delete(0, 'end')
        self.entries["Email"].insert(0, str(item_values[11]) if item_values[11] != "None" else "")
        
        self.entries["Contact Number"].delete(0, 'end')
        self.entries["Contact Number"].insert(0, str(item_values[12]) if item_values[12] != "None" else "")

        # Populate Checkboxes
        self.check_vars["Agreement Signed"].set(1 if item_values[13] == "Yes" else 0)
        self.check_vars["Advance Paid"].set(1 if item_values[14] == "Yes" else 0)
        self.check_vars["Deposit Paid"].set(1 if item_values[15] == "Yes" else 0)

    def delete_tenant(self):
        selected_item = self.tenant_table.selection()
        if not selected_item:
            return # Nothing is selected
            
        # Get the ID of the selected tenant
        tenant_id = self.tenant_table.item(selected_item[0])['values'][0]
        
        # Delete from SQLite database
        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
        conn.commit()
        conn.close()
        
        self.load_tenants_from_db()

    def clear_form(self):
        # Wipes all data from the form
        for field, ent in self.entries.items():
            if field in ["Date Started", "Move Out Date"]:
                ent.set_date(time.strftime('%Y-%m-%d'))
            else:
                ent.delete(0, 'end')
        for var in self.check_vars.values():
            var.set(0)
            
        self.editing_tenant_id = None
        self.save_btn.configure(text="Save Tenant", fg_color="green", hover_color="darkgreen")

    def save_tenant_to_db(self):
        data = [self.entries[field].get() for field in self.fields]
        data.extend([self.check_vars[check].get() for check in self.check_vars])

        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()
        
        if self.editing_tenant_id:
            # If editing, we UPDATE instead of INSERT
            data.append(self.editing_tenant_id)
            cursor.execute('''
                UPDATE tenants SET
                    full_name=?, address=?, room_number=?, date_started=?, lease_term=?, move_out_date=?,
                    monthly_due=?, valid_id=?, job=?, messenger_link=?, email=?, contact_number=?,
                    agreement_signed=?, advance_paid=?, deposit_paid=?
                WHERE id=?
            ''', data)
        else:
            # If completely new, we INSERT
            cursor.execute('''
                INSERT INTO tenants (
                    full_name, address, room_number, date_started, lease_term, move_out_date,
                    monthly_due, valid_id, job, messenger_link, email, contact_number,
                    agreement_signed, advance_paid, deposit_paid
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        cursor.execute("SELECT * FROM tenants")
        rows = cursor.fetchall()
        
        for row in rows:
            formatted_row = list(row)
            formatted_row[13] = "Yes" if formatted_row[13] == 1 else "No" 
            formatted_row[14] = "Yes" if formatted_row[14] == 1 else "No" 
            formatted_row[15] = "Yes" if formatted_row[15] == 1 else "No" 
            
            self.tenant_table.insert("", "end", values=formatted_row)
            
        conn.close()

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = TenantTrackerApp()
    app.mainloop()