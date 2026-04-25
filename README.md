A lightweight, self-hosted web dashboard for managing chicken batches, hatch tracking, and flock data.

Built with Python and Flask, this app is designed for small hatcheries and backyard breeders who want a simple way to track bird ages, hatch rates, and flock changes—all in one place.

---

## 🚀 Features

### 🐣 Batch Tracking
- Track chicken batches by breed
- Automatically calculate age (days & weeks)
- Store:
  - Hatch date
  - Hens / roosters / unsexed counts
  - Notes

### 📊 Dashboard
- Clean web interface
- View all batches in one table
- See total birds across all batches
- Mobile-friendly (works on phones)

### 🧾 Event Logging
- Track:
  - Deaths
  - Sales
  - Transfers
- Keeps historical records instead of just totals

### 🥚 Incubation Tracking
- Track eggs before hatch
- Expected hatch date (auto-calculated)
- Hatch success rate

### 🔔 Alerts
- Upcoming hatch dates
- Age milestones
- Custom reminders

### 📈 Analytics
- Hatch rate
- Survival rate
- Population trends

### 🔐 Authentication
- Login system with password hashing
- Session-based authentication

### 💾 Backup & Restore
- Export data (JSON/CSV)
- Import backups

---

## 🛠 Tech Stack

- Python 3
- Flask
- SQLite
- HTML + CSS (lightweight, no heavy frameworks)

---

## 📦 Installation (VS Code)

### 1. Download, Extract
Download zip, extract it.

2. Open in VS Code
Open VS Code
Click File → Open Folder
Select the project folder
3. Create a Virtual Environment (Recommended)
python -m venv venv

Activate it:

    Windows:

       venv\Scripts\activate

    Mac/Linux:

        source venv/bin/activate
        
4. Install Dependencies
   pip install -r requirements.txt
5. Run the Application
   python app.py
6. Open in Browser

Go to:

http://127.0.0.1:5000

Or from another device on your network:

http://YOUR-IP-ADDRESS:5000


You can modify:

Port in app.py
Secret key for sessions
Default login credentials
🔮 Future Plans
Individual bird tracking
Multi-user accounts
Cloud sync
Notifications (email or push)
🤝 Contributing

Pull requests are welcome. If you have ideas for improvements, feel free to open an issue.

📜 License

This project is licensed under the MIT License — see the LICENSE file for details.

🐓 About

Built for real hatchery use by Seabreeze Hatchery.
Simple, practical, and built to run 24/7 without complexity.
