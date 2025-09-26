from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import json
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# User authentication
USERS = {
    "H7": {"password": "00Q11", "isAdmin": True},
    "A7": {"password": "1122QQ", "isAdmin": False}
}

# Default tasks
DEFAULT_TASKS = [
    {"id": 1, "label": "Subah 6 AM uthna + Exercise", "category": "morning"},
    {"id": 2, "label": "Breakfast + Daily Planning", "category": "morning"},
    {"id": 3, "label": "College Lectures Attend karna", "category": "college"},
    {"id": 4, "label": "Practical Lab Work Complete karna", "category": "college"},
    {"id": 5, "label": "Lunch Break + Rest", "category": "college"},
    {"id": 6, "label": "Library me 2 hours self-study", "category": "study"},
    {"id": 7, "label": "Assignment/Project Work", "category": "study"},
    {"id": 8, "label": "Evening Snacks + Break", "category": "evening"},
    {"id": 9, "label": "Revision of Today's Topics", "category": "study"},
    {"id": 10, "label": "Skill Development (CAD/Software)", "category": "skill"},
    {"id": 11, "label": "Dinner + Family Time", "category": "evening"},
    {"id": 12, "label": "Relaxation (Music/Movie/Reading)", "category": "night"}
]

# Rewards
REWARDS = [
    {"id": 1, "name": "30 mins Gaming", "cost": 5, "description": "30 minutes gaming session"},
    {"id": 2, "name": "1 Hour Phone Time", "cost": 8, "description": "Extra 1 hour phone usage"},
    {"id": 3, "name": "Movie Night", "cost": 15, "description": "Full movie of your choice"},
    {"id": 4, "name": "Favorite Snacks", "cost": 10, "description": "Your favorite snacks pack"},
    {"id": 5, "name": "Stationery Item", "cost": 20, "description": "New pen, notebook, etc."},
    {"id": 6, "name": "Day Off", "cost": 50, "description": "One complete day off from routine"}
]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_data(username):
    data_file = f"data/{username}.json"
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            return json.load(f)
    else:
        # Initialize new user data
        return {
            "totalStars": 0,
            "availableStars": 0,
            "lifetimeStars": 0,
            "rewardsPurchased": [],
            "dailyData": {},
            "tasks": DEFAULT_TASKS.copy()
        }

def save_user_data(username, data):
    os.makedirs("data", exist_ok=True)
    data_file = f"data/{username}.json"
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and USERS[username]['password'] == password:
            session['username'] = username
            session['is_admin'] = USERS[username]['isAdmin']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_data = get_user_data(session['username'])
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Prevent future dates
    today = datetime.now().strftime('%Y-%m-%d')
    if selected_date > today:
        selected_date = today
    
    # Initialize date data if not exists
    if selected_date not in user_data['dailyData']:
        user_data['dailyData'][selected_date] = {
            "tasksCompleted": [],
            "starsEarned": 0,
            "date": selected_date
        }
        save_user_data(session['username'], user_data)
    
    return render_template('dashboard.html', 
                         user_data=user_data,
                         selected_date=selected_date,
                         today=today,
                         is_admin=session.get('is_admin', False))

@app.route('/api/toggle_task', methods=['POST'])
@login_required
def toggle_task():
    data = request.json
    task_id = data.get('task_id')
    completed = data.get('completed')
    selected_date = data.get('date')
    
    user_data = get_user_data(session['username'])
    
    # Prevent modifying future dates
    today = datetime.now().strftime('%Y-%m-%d')
    if selected_date > today:
        return jsonify({"success": False, "error": "Cannot modify future dates"})
    
    if selected_date not in user_data['dailyData']:
        user_data['dailyData'][selected_date] = {
            "tasksCompleted": [],
            "starsEarned": 0,
            "date": selected_date
        }
    
    date_data = user_data['dailyData'][selected_date]
    
    if completed:
        if task_id not in date_data['tasksCompleted']:
            date_data['tasksCompleted'].append(task_id)
            date_data['starsEarned'] += 1
            user_data['totalStars'] += 1
            user_data['availableStars'] += 1
            user_data['lifetimeStars'] += 1
    else:
        if task_id in date_data['tasksCompleted']:
            date_data['tasksCompleted'].remove(task_id)
            date_data['starsEarned'] -= 1
            user_data['totalStars'] -= 1
            user_data['availableStars'] -= 1
            user_data['lifetimeStars'] -= 1
    
    save_user_data(session['username'], user_data)
    return jsonify({"success": True, "stars": date_data['starsEarned']})

@app.route('/api/purchase_reward', methods=['POST'])
@login_required
def purchase_reward():
    data = request.json
    reward_id = data.get('reward_id')
    
    user_data = get_user_data(session['username'])
    reward = next((r for r in REWARDS if r['id'] == reward_id), None)
    
    if not reward:
        return jsonify({"success": False, "error": "Reward not found"})
    
    if user_data['availableStars'] >= reward['cost']:
        user_data['availableStars'] -= reward['cost']
        user_data['rewardsPurchased'].append(reward_id)
        save_user_data(session['username'], user_data)
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Not enough stars"})

@app.route('/api/reset_tasks', methods=['POST'])
@login_required
def reset_tasks():
    data = request.json
    selected_date = data.get('date')
    
    user_data = get_user_data(session['username'])
    
    if selected_date in user_data['dailyData']:
        date_data = user_data['dailyData'][selected_date]
        
        # Subtract stars earned on this date
        user_data['totalStars'] -= date_data['starsEarned']
        user_data['availableStars'] -= date_data['starsEarned']
        user_data['lifetimeStars'] -= date_data['starsEarned']
        
        # Reset date data
        date_data['tasksCompleted'] = []
        date_data['starsEarned'] = 0
        
        save_user_data(session['username'], user_data)
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Date not found"})

@app.route('/api/update_tasks', methods=['POST'])
@login_required
def update_tasks():
    if not session.get('is_admin'):
        return jsonify({"success": False, "error": "Admin rights required"})
    
    data = request.json
    new_tasks = data.get('tasks')
    
    user_data = get_user_data(session['username'])
    
    # Update tasks
    user_data['tasks'] = []
    for i, task_label in enumerate(new_tasks, 1):
        user_data['tasks'].append({
            "id": i,
            "label": task_label,
            "category": "custom"
        })
    
    save_user_data(session['username'], user_data)
    return jsonify({"success": True})

@app.route('/rewards')
@login_required
def rewards():
    user_data = get_user_data(session['username'])
    return render_template('rewards.html', 
                         user_data=user_data,
                         rewards=REWARDS,
                         is_admin=session.get('is_admin', False))

@app.route('/progress')
@login_required
def progress():
    user_data = get_user_data(session['username'])
    
    # Calculate progress percentages
    now = datetime.now()
    start_of_year = datetime(now.year, 1, 1)
    days_passed = (now - start_of_year).days + 1
    max_yearly_stars = days_passed * 12
    
    weekly_percent = min((user_data['lifetimeStars'] / (52 * 12)) * 100, 100)
    monthly_percent = min((user_data['lifetimeStars'] / (12 * 30 * 12)) * 100, 100)
    yearly_percent = min((user_data['lifetimeStars'] / max_yearly_stars) * 100, 100) if max_yearly_stars > 0 else 0
    
    return render_template('progress.html',
                         user_data=user_data,
                         weekly_percent=weekly_percent,
                         monthly_percent=monthly_percent,
                         yearly_percent=yearly_percent,
                         is_admin=session.get('is_admin', False))

@app.route('/calendar')
@login_required
def calendar():
    user_data = get_user_data(session['username'])
    
    month = int(request.args.get('month', datetime.now().month)) - 1
    year = int(request.args.get('year', datetime.now().year))
    
    # Generate calendar data
    calendar_data = generate_calendar(year, month, user_data['dailyData'])
    
    return render_template('calendar.html',
                         user_data=user_data,
                         calendar_data=calendar_data,
                         month=month,
                         year=year,
                         is_admin=session.get('is_admin', False))

def generate_calendar(year, month, daily_data):
    first_day = datetime(year, month + 1, 1)
    days_in_month = (datetime(year, month + 2, 1) - timedelta(days=1)).day
    
    calendar = []
    
    # Add empty days for the first week
    for i in range(first_day.weekday()):
        calendar.append({"day": 0, "date": None, "stars": 0})
    
    # Add days of the month
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month+1:02d}-{day:02d}"
        stars = daily_data.get(date_str, {}).get('starsEarned', 0)
        calendar.append({"day": day, "date": date_str, "stars": stars})
    
    return calendar

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)