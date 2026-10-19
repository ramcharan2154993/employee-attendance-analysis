# AttendIQ — Production Deployment Guide

This guide is a complete, beginner-friendly walkthrough for deploying **AttendIQ** to **PythonAnywhere** (free tier with MySQL). Follow the steps in order; each step includes exact commands to copy and paste.

---

## 1. Create a PythonAnywhere Account & Open Bash Console

1. Go to [pythonanywhere.com](https://www.pythonanywhere.com) and register a free **"Beginner"** account.
   - Note: Your PythonAnywhere username will form part of your web address (`yourusername.pythonanywhere.com`) and your MySQL database name (`yourusername$dbname`).
2. Log in and navigate to the **Dashboard**.
3. Under **"New console"**, click **"Bash"**. This opens an in-browser Linux terminal.

---

## 2. Clone the GitHub Repository

In your Bash console, clone the repository into your home directory:

```bash
git clone https://github.com/ramcharan2154993/employee-attendance-analysis.git
cd employee-attendance-analysis
```

### If Your Repository Is Private:
GitHub requires a **Personal Access Token (Classic)** instead of your account password:
1. On GitHub: go to **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
2. Click **Generate new token (classic)**, check the `repo` scope, and generate.
3. In the PythonAnywhere console, enter your GitHub username when prompted, and paste the generated personal access token as the password.
4. **Security Notice**: Never save tokens in repository files or scripts. Enter them interactively at the git prompt.

---

## 3. Create a Virtual Environment & Install Dependencies

Ensure your virtual environment matches the Python version you intend to choose on the PythonAnywhere **Web** tab (recommended: **Python 3.10**):

```bash
# Verify you are in the project folder
pwd
# Expected output: /home/yourusername/employee-attendance-analysis

# Create virtualenv with python3.10
virtualenv --python=python3.10 ~/.virtualenvs/attendiq-env

# Activate virtualenv
source ~/.virtualenvs/attendiq-env/bin/activate

# Upgrade pip and install all pinned production requirements
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Create the MySQL Database

1. On the PythonAnywhere top menu, click the **Databases** tab.
2. Scroll to the **MySQL database** section.
3. If this is your first time using MySQL on PythonAnywhere, set a strong MySQL password. Keep this password safe (you will need it in step 5).
4. Under **"Create database"**, enter `attendance_db` and click **"Create"**.
5. PythonAnywhere will prefix your database name with your username:
   - Full Database Name: `yourusername$attendance_db`
   - MySQL Host: Look at the top of the Databases page under **"Connecting from outside PythonAnywhere"** or **"Connecting from PythonAnywhere"**. It will look like:
     `yourusername.mysql.pythonanywhere-services.com`
     > **Important**: The database host is **NOT** `localhost`. Always use your service hostname!
   - MySQL User: `yourusername`
   - Port: `3306`

---

## 5. Create the Server-Side `.env` Configuration File

> **Security Rule**: The `.env` file must exist **ONLY** on the server. Never commit `.env` to Git.

In your PythonAnywhere Bash console (still inside `/home/yourusername/employee-attendance-analysis`):

1. Generate a strong, cryptographically secure 64-character secret key:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copy the output string.

2. Create your `.env` file using `nano`:
   ```bash
   nano .env
   ```

3. Paste the following configuration (replace placeholders with your real values from Step 4 and the key generated above):
   ```env
   # Database credentials (from PythonAnywhere Databases tab)
   DB_HOST=yourusername.mysql.pythonanywhere-services.com
   DB_PORT=3306
   DB_USER=yourusername
   DB_PASSWORD=your_mysql_password_here
   DB_NAME=yourusername$attendance_db
   DB_TEST_NAME=yourusername$attendance_db_test

   # Production environment flags
   APP_ENV=production
   SECRET_KEY=paste_the_64_character_generated_token_here
   TRUSTED_PROXY_COUNT=1
   ```

4. Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit `nano`.
5. Restrict permissions so only your user can read `.env`:
   ```bash
   chmod 600 .env
   ```

---

## 6. Initialize Schema & Provision First Administrator

Run the idempotent database migration script to build the tables, constraints, and audit log. Then run the interactive admin creation CLI:

```bash
# Ensure virtualenv is active
source ~/.virtualenvs/attendiq-env/bin/activate

# 1. Run database migration
python -m src.db

# 2. Interactively create your master administrator
python -m src.create_admin
```

When prompted by `python -m src.create_admin`:
- Enter an admin username (e.g. `admin`).
- Enter a strong password (minimum 10 characters).
- Confirm the password.

You will see confirmation:
```text
Admin user 'admin' created successfully with user ID 1.
```

---

## 7. Configure the PythonAnywhere Web Tab

1. Click the **Web** tab on the PythonAnywhere dashboard.
2. Click **"Add a new web app"**.
3. Accept your free domain name (`yourusername.pythonanywhere.com`) and click **Next**.
4. When prompted to select a Python framework, choose **"Manual configuration"** (do **not** choose "Flask").
5. Choose **Python 3.10** and click **Next**.
6. Once created, configure the fields in the Web tab as follows:

### Paths Configuration
- **Source code**: `/home/yourusername/employee-attendance-analysis`
- **Working directory**: `/home/yourusername/employee-attendance-analysis`
- **Virtualenv**: `/home/yourusername/.virtualenvs/attendiq-env`

### Static Files Mapping
Scroll down to the **Static files** section and add this entry:
- **URL**: `/static/`
- **Directory**: `/home/yourusername/employee-attendance-analysis/src/web/static`

### Security Configuration
- Under **Security**, toggle **"Force HTTPS"** to **Enabled**.

### Edit the WSGI Configuration File
In the **Code** section of the Web tab, click the link to your **WSGI configuration file** (e.g. `/var/www/yourusername_pythonanywhere_com_wsgi.py`).

Delete all default contents in that file and paste the following snippet:

```python
import os
import sys

# Define path to application root
project_home = '/home/yourusername/employee-attendance-analysis'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from the server-side .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Import WSGI application instance
from wsgi import application
```
*(Make sure to replace `yourusername` with your actual PythonAnywhere username!)*

Click the green **"Save"** button at the top right of the editor.

### Reload the Web App
Go back to the **Web** tab and click the big green **"Reload yourusername.pythonanywhere.com"** button.

---

## 8. Post-Deployment Verification Checklist

Verify each of the following in your web browser:

1. **Health Check Endpoint**:
   - Open: `https://yourusername.pythonanywhere.com/healthz`
   - Expect: Plain text `ok` with HTTP 200.
2. **TLS / HTTPS Padlock**:
   - Confirm your browser shows the secure padlock icon (`https://`).
3. **Login**:
   - Navigate to `https://yourusername.pythonanywhere.com/login`.
   - Log in with the credentials created in Step 6 (`admin`).
4. **Create HR User**:
   - Go to **User Accounts** (`/users`).
   - Create a standard HR operator account (e.g., `hr_ops`) with the `HR` role.
5. **Staff Directory & Attendance Entry**:
   - Navigate to **Employees** (`/employees`) and add an active employee.
   - Navigate to **Attendance** (`/attendance/department`) and mark attendance for a department roster.
6. **Reports & Analytics**:
   - Visit `/summary/employees`, `/summary/departments`, and `/ranking`.
   - Visit `/charts` and confirm matplotlib visualization charts render correctly.
7. **Security Headers**:
   - In browser DevTools (F12) → **Network** tab → click the first document request → **Headers**.
   - Confirm headers are present:
     - `Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'`
     - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`

---

## 9. How to Deploy Future Updates

When you commit and push updates from your local computer:

1. On your local PC:
   ```bash
   git push origin main
   ```
2. In PythonAnywhere Bash console:
   ```bash
   cd ~/employee-attendance-analysis
   git pull origin main
   source ~/.virtualenvs/attendiq-env/bin/activate
   pip install -r requirements.txt
   python -m src.db
   ```
3. On the PythonAnywhere **Web** tab, click **"Reload"**.

---

## 10. Troubleshooting Guide

Where to find logs:
- On the **Web** tab, under **Log files**, inspect:
  - **Error log**: `/var/log/yourusername.pythonanywhere.com.error.log`
  - **Server log**: `/var/log/yourusername.pythonanywhere.com.server.log`
  - **Access log**: `/var/log/yourusername.pythonanywhere.com.access.log`

Common errors and solutions:

| Error | Root Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'src'` | Working directory or sys.path not configured in WSGI file | In WSGI file, verify `sys.path.insert(0, '/home/yourusername/employee-attendance-analysis')`. |
| `RuntimeError: SECRET_KEY is not set` or `too weak` | Missing `.env` or weak secret key | Check `~/.employee-attendance-analysis/.env` exists and has `SECRET_KEY` >= 32 chars. Verify `load_dotenv` in WSGI file. |
| `mysql.connector.errors.ProgrammingError: Access denied` | Incorrect MySQL credentials | Verify `DB_USER`, `DB_PASSWORD`, and `DB_HOST` in `.env`. Host must be `yourusername.mysql.pythonanywhere-services.com`. |
| `502 Bad Gateway` / `Unhandled exception` | Syntax or unhandled error during startup | Open the **Error log** from the Web tab to view the full Python traceback. |
| Static CSS/Fonts Not Loading (404 on `/static/...`) | Static file mapping missing | On the Web tab, verify `/static/` maps to `/home/yourusername/employee-attendance-analysis/src/web/static`. |

---

## 11. Alternative: Render + External MySQL

If deploying to [Render](https://render.com) using an external managed MySQL database (e.g. Aiven, PlanetScale, or AWS RDS):

1. **Repository**: Connect your GitHub repository to Render as a **Web Service**.
2. **Environment**: Python 3.
3. **Build Command**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Start Command**:
   ```bash
   gunicorn wsgi:application
   ```
5. **Environment Variables** (in Render Dashboard):
   - `APP_ENV`: `production`
   - `SECRET_KEY`: *(Generate 64-char hex token)*
   - `DB_HOST`: `your-database-hostname.com`
   - `DB_PORT`: `3306`
   - `DB_USER`: `your_db_user`
   - `DB_PASSWORD`: `your_db_password`
   - `DB_NAME`: `attendance_db`
   - `TRUSTED_PROXY_COUNT`: `1`

---

## 12. Post-Launch Maintenance & Security Checklist

- [ ] **Rotate MySQL & Admin Passwords**: Rotate database and administrative passwords every 90 days.
- [ ] **Automated Database Backups**: Run regular backups in your Bash console:
  ```bash
  mysqldump -u yourusername -h yourusername.mysql.pythonanywhere-services.com -p 'yourusername$attendance_db' > backup_$(date +%F).sql
  ```
  Store encrypted backups off-site.
- [ ] **Keep Dependencies Updated**: Regularly audit and upgrade packages:
  ```bash
  pip list --outdated
  ```
- [ ] **Never Share or Check In `.env`**: Always confirm `.gitignore` prevents `.env` and database dumps from being committed.
