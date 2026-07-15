import customtkinter as ctk
import time
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
        # Header Frame
        self.header_frame = ctk.CTkFrame(self.tab_tenants, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=10)

        # Title
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Tenant Management", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(side="left")

        # Live Clock
        self.clock_label = ctk.CTkLabel(
            self.header_frame, 
            text="", 
            font=ctk.CTkFont(size=14)
        )
        self.clock_label.pack(side="right")

        # Start clock loop
        self.update_clock()

    def update_clock(self):
        # Time format: 03:23:53 PM | July 15, 2026
        current_time = time.strftime('%I:%M:%S %p | %B %d, %Y')
        self.clock_label.configure(text=current_time)
        self.after(1000, self.update_clock)

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    
    app = TenantTrackerApp()
    app.mainloop()