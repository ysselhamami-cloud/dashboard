# OurHelpdesk

OurHelpdesk is a Flask helpdesk demo with role-based authentication and role-specific workspaces.

## Demo accounts
- **client / client** → create and track own tickets.
- **itdev / itdev** → tickets, interventions, customers.
- **admin / admin** → dashboard, tickets, interventions, profile/settings.

## Steps to enter the web app
1. Open a terminal in this project folder.
2. Install Flask (if not already installed):
   ```bash
   python -m pip install flask
   ```
3. Start the application:
   ```bash
   python app.py
   ```
4. Open your browser and go to:
   `http://127.0.0.1:5000`
5. On the login page, sign in with one of the demo accounts above.

## Run
```bash
python app.py
```
