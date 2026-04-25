# Chicken Hatchery Dashboard - Upgrade Guide

This guide provides instructions to upgrade your existing Chicken Hatchery Dashboard application to the new version with enhanced features.

## 1. Backup Your Data (Crucial!)
Before proceeding, **always back up your existing `hatchery.db` file**. If anything goes wrong, you can revert to this backup.

```bash
# Stop the service first
sudo systemctl stop hatchery.service

# Navigate to your app directory
cd /opt/hatchery_app

# Copy your database file to a safe location
cp hatchery.db hatchery_backup_$(date +%Y%m%d_%H%M%S).db
```

## 2. Update Application Files

Replace your existing `app.py`, `templates/`, and `static/css/style.css` files with the new versions. If you are using Git, you can pull the latest changes:

```bash
cd /opt/hatchery_app
git pull
```

If you are manually copying files, ensure the following files are updated:
*   `app.py`
*   `templates/layout.html`
*   `templates/dashboard.html`
*   `templates/batch_form.html`
*   `templates/incubation.html`
*   `templates/events.html`
*   `templates/analytics.html`
*   `templates/inventory.html` (new file)
*   `static/css/style.css`

## 3. Run Database Migration

New tables and columns have been added. You need to run a migration script to update your `hatchery.db` file. 

1.  **Create the migration script:**
    Create a new file named `migrate.py` in your `/opt/hatchery_app` directory:
    ```bash
    nano /opt/hatchery_app/migrate.py
    ```

2.  **Paste the following content into `migrate.py`:**
    ```python
    import sqlite3
    from datetime import datetime

    DATABASE = 'hatchery.db'

    def get_db():
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        return db

    def migrate():
        db = get_db()
        cursor = db.cursor()

        print("Starting database migration...")

        # Add new columns to existing tables
        try:
            cursor.execute("ALTER TABLE batches ADD COLUMN health_status TEXT DEFAULT 'Healthy'")
            cursor.execute("ALTER TABLE batches ADD COLUMN health_notes TEXT")
            print("Added health_status and health_notes to batches table.")
        except sqlite3.OperationalError as e:
            print(f"Columns already exist or error: {e}")

        try:
            cursor.execute("ALTER TABLE incubation_batches ADD COLUMN daily_temp_log TEXT")
            cursor.execute("ALTER TABLE incubation_batches ADD COLUMN daily_humidity_log TEXT")
            cursor.execute("ALTER TABLE incubation_batches ADD COLUMN lockdown_date TEXT")
            print("Added daily_temp_log, daily_humidity_log, lockdown_date to incubation_batches table.")
        except sqlite3.OperationalError as e:
            print(f"Columns already exist or error: {e}")

        # Create new tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                task_date TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
            )
        """)
        print("Created daily_tasks table (if not exists).")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environment_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date TEXT NOT NULL UNIQUE,
                temperature REAL,
                humidity REAL,
                notes TEXT
            )
        """)
        print("Created environment_logs table (if not exists).")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL UNIQUE,
                quantity INTEGER NOT NULL DEFAULT 0,
                unit TEXT,
                low_threshold INTEGER NOT NULL DEFAULT 0
            )
        """)
        print("Created inventory table (if not exists).")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_date TEXT NOT NULL,
                batch_id INTEGER,
                quantity_sold INTEGER NOT NULL,
                price_per_bird REAL NOT NULL,
                notes TEXT,
                FOREIGN KEY (batch_id) REFERENCES batches (id)
            )
        """)
        print("Created sales table (if not exists).")

        db.commit()
        db.close()
        print("Database migration complete.")

    if __name__ == '__main__':
        migrate()
    ```

3.  **Run the migration script:**
    ```bash
    cd /opt/hatchery_app
    ./venv/bin/python3 migrate.py
    ```
    You should see messages indicating the tables and columns were added.

## 4. Restart the Application Service

After the migration is complete, restart the systemd service to load the new application code and database schema:

```bash
sudo systemctl daemon-reload
sudo systemctl restart hatchery.service
```

## 5. Verify the Upgrade

Open your web browser and navigate to your dashboard. You should now see the new sections for "Today at the Hatchery," daily tasks, environment logging, and new navigation links for Inventory. Check the batch and incubation forms for the new fields.

## 6. Example Data (Optional)

To populate some of the new tables with example data, you can manually add entries via the new forms (e.g., add inventory items, log environment data, create daily tasks). The application will automatically create default daily tasks for the current day when you visit the dashboard.
