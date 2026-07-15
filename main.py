import customtkinter as ctk
import time
import sqlite3
from database import init_db

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

        self.setup_tenant_tab()

    def setup_tenant_tab(self):
        # --- HEADER ---
        self.header_frame = ctk.CTkFrame(self.tab_tenants, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=10)

        self.title_label = ctk.CTkLabel(self.header_frame, text="Tenant Management", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left")

        self.clock_label = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=14))
        self.clock_label.pack(side="right")
        self.update_clock()

        # --- CONTENT LAYOUT (Left Form, Right Table) ---
        self.tenant_content = ctk.CTkFrame(self.tab_tenants, fg_color="transparent")
        self.tenant_content.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: Scrollable Input Form
        self.form_frame = ctk.CTkScrollableFrame(self.tenant_content, width=350, label_text="Add New Tenant")
        self.form_frame.pack(side="left", fill="y", padx=(0, 10))

        # Form Fields
        self.entries = {}
        fields = [
            "Full Name", "Address", "Room Number", "Date Started",
            "Lease Term", "Move Out Date", "Monthly Due",
            "Valid ID", "Working/Job", "Messenger Link",
            "Email", "Contact Number"
        ]

        for field in fields:
            lbl = ctk.CTkLabel(self.form_frame, text=field)
            lbl.pack(anchor="w", padx=10, pady=(5, 0))
            ent = ctk.CTkEntry(self.form_frame, width=300)
            ent.pack(padx=10, pady=(0, 5))
            self.entries[field] = ent

        # Checkboxes
        self.check_vars = {
            "Agreement Signed": ctk.IntVar(),
            "Advance Paid": ctk.IntVar(),
            "Deposit Paid": ctk.IntVar()
        }

        for check_name, var in self.check_vars.items():
            chk = ctk.CTkCheckBox(self.form_frame, text=check_name, variable=var)
            chk.pack(anchor="w", padx=10, pady=5)

        # Save Button
        self.save_btn = ctk.CTkButton(self.form_frame, text="Save Tenant", command=self.save_tenant_to_db, fg_color="green", hover_color="darkgreen")
        self.save_btn.pack(pady=20, padx=10, fill="x")

        # Right: Display Table (Placeholder for next step)
        self.table_frame = ctk.CTkFrame(self.tenant_content)
        self.table_frame.pack(side="right", fill="both", expand=True)
        
        self.table_placeholder = ctk.CTkLabel(self.table_frame, text="[ Tenant Data Table Will Appear Here ]", text_color="gray")
        self.table_placeholder.pack(expand=True)

    def update_clock(self):
        current_time = time.strftime('%I:%M:%S %p | %B %d, %Y')
        self.clock_label.configure(text=current_time)
        self.after(1000, self.update_clock)

    def save_tenant_to_db(self):
        # Extract data from the form
        data = [self.entries[field].get() for field in self.entries]
        data.extend([self.check_vars[check].get() for check in self.check_vars])

        # Connect and insert into database
        conn = sqlite3.connect('tenant_tracker.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tenants (
                full_name, address, room_number, date_started, lease_term, move_out_date,
                monthly_due, valid_id, job, messenger_link, email, contact_number,
                agreement_signed, advance_paid, deposit_paid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        conn.commit()
        conn.close()

        # Clear the form fields after saving
        for ent in self.entries.values():
            ent.delete(0, 'end')
        for var in self.check_vars.values():
            var.set(0)
            
        print("Tenant saved to database successfully!")

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = TenantTrackerApp()
    app.mainloop()