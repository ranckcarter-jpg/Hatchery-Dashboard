# Chicken Hatchery Dashboard - Setup and Deployment Guide

This guide provides instructions for setting up and deploying the Flask-based Chicken Hatchery Dashboard application.

## 1. Prerequisites

*   Python 3.8+ installed on your system.
*   `pip` (Python package installer) installed.
*   Basic understanding of the Linux command line.

## 2. Installation Steps

1.  **Clone or Download the Application:**

    If you have `git` installed, you can clone the repository:
    ```bash
    git clone <repository_url> # Replace with actual repository URL if applicable
    cd hatchery_app
    ```
    Otherwise, download the `hatchery_app` folder and navigate into it:
    ```bash
    cd path/to/hatchery_app
    ```

2.  **Create a Virtual Environment (Recommended):**

    It is highly recommended to use a Python virtual environment to manage dependencies.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**

    Install the required Python packages using `pip`:
    ```bash
    pip install -r requirements.txt
    ```

## 3. Running the Application

1.  **Initialize the Database:**

    The application will automatically initialize the SQLite database (`hatchery.db`) and create a default admin user (`admin` / `admin123`) on its first run. You can run it once to set this up:
    ```bash
    python app.py
    ```
    Press `Ctrl+C` after you see the message `* Running on http://0.0.0.0:5000/` to stop the initial run.

2.  **Start the Application:**

    To run the application in development mode (with debugging enabled):
    ```bash
    python app.py
    ```
    For production, it's recommended to use a WSGI server like Gunicorn. First, install Gunicorn:
    ```bash
    pip install gunicorn
    ```
    Then run:
    ```bash
    gunicorn -w 4 -b 0.0.0.0:5000 app:app
    ```
    (This example uses 4 worker processes; adjust as needed.)

## 4. Accessing the Dashboard

Once the application is running, you can access it from any device on your local network:

1.  **Find your server's IP address:**

    On your Proxmox LXC container, you can find its IP address using:
    ```bash
    ip a
    ```
    Look for an IP address like `192.168.x.x` or `10.0.x.x` associated with your network interface.

2.  **Open in a Web Browser:**

    On any device connected to the same network, open a web browser and navigate to:
    ```
    http://<your_server_ip_address>:5000
    ```
    For example, if your server's IP is `192.168.1.100`, you would go to `http://192.168.1.100:5000`.

## 5. Systemd Service (for Production)

To ensure the application starts automatically on boot and runs reliably, you can set it up as a systemd service.

1.  **Create the service file:**

    Create a file named `hatchery.service` in `/etc/systemd/system/`:
    ```bash
    sudo nano /etc/systemd/system/hatchery.service
    ```

2.  **Add the following content to `hatchery.service`:**

    (Make sure to replace `/path/to/your/hatchery_app` with the actual absolute path to your application directory and `your_username` with your Linux username.)

    ```ini
    [Unit]
    Description=Flask Hatchery Dashboard Application
    After=network.target

    [Service]
    User=your_username
    WorkingDirectory=/path/to/your/hatchery_app
    ExecStart=/path/to/your/hatchery_app/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Reload systemd, enable, and start the service:**

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable hatchery.service
    sudo systemctl start hatchery.service
    ```

4.  **Check the service status:**

    ```bash
    sudo systemctl status hatchery.service
    ```

    You should see `active (running)`.

## 6. Backup and Restore

*   **Backup:** Navigate to the `/backup` route in the application to download a JSON backup of your data.
*   **Restore:** To restore, you would typically replace the `hatchery.db` file with a backed-up version. Ensure the application is stopped before replacing the database file. For more complex scenarios, you might need to write a script to import the JSON data into a new database.
