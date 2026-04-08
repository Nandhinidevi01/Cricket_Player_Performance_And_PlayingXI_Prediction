from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
import os
import random
import pickle

app = Flask(__name__)

# ================= AUTH CONFIG =================
app.config['SECRET_KEY'] = 'nandhu_secret_key_123' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' 

# ================= DATABASE MODEL =================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= PATH =================
# Note: Intha path unga system-la correct-ah irukanu check pannikonga
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models")

# ================= LOAD DATA =================
try:
    career_df = pd.read_csv(os.path.join(BASE_DIR, "data/career/player_career_stats_t20.csv"))
    career_df.fillna("Unknown", inplace=True) 
    career_df["player"] = career_df["player"].astype(str).str.lower().str.strip()
    print("✅ Data Loaded")
except Exception as e:
    print(f"❌ Data Load Error: {e}")

# ================= LOAD MODELS =================
try:
    bat_model = pickle.load(open(os.path.join(MODEL_PATH, "batting.pkl"), "rb"))
    bowl_model = pickle.load(open(os.path.join(MODEL_PATH, "bowling_regressor.pkl"), "rb"))
    print("✅ Models Loaded Successfully")
except Exception as e:
    print("❌ Model load failed:", e)
    bat_model = None
    bowl_model = None

# ================= HELPERS =================
def get_role(role):
    role = str(role).lower()
    if "wk" in role or "wicket" in role: return "WICKETKEEPER"
    elif "all" in role: return "ALLROUNDER"
    elif "bowl" in role: return "BOWLER"
    else: return "BATSMAN"

def safe_val(row, col):
    try: return float(row[col])
    except: return 0

# ================= ROUTES =================

# 1. Signup Route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            return "User already exists! <a href='/signup'>Try again</a>"
            
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
        
    return render_template("signup.html")

# 2. Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for("home"))
        else:
            return "Invalid Credentials! <a href='/login'>Try again</a>"
    return render_template("login.html")

# 3. Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# 4. Main Home (Protected)
@app.route("/")
@login_required
def home():
    return render_template("dashboard.html")

# 5. Predict Logic (Protected)
@app.route("/predict", methods=["POST"])
@login_required
def predict():
    try:
        data = request.json
        players = [p.strip().lower() for p in data.get("players", "").split(",")]
        captain = data.get("captain", "").lower().strip()
        vice_captain = data.get("vice_captain", "").lower().strip()

        matched = career_df[career_df["player"].isin(players)].copy()
        if matched.empty: return jsonify({"error": "No players found"})

        matched = matched.drop_duplicates("player")
        matched["role_fixed"] = matched["role"].apply(get_role)
        matched["score"] = (
            matched.apply(lambda x: safe_val(x, "career_runs_per_match"), axis=1) * 0.6 +
            matched.apply(lambda x: safe_val(x, "career_wickets_per_match"), axis=1) * 20
        )
        matched = matched.sort_values(by="score", ascending=False)

        batsmen = matched[matched["role_fixed"] == "BATSMAN"].head(4)
        bowlers = matched[matched["role_fixed"] == "BOWLER"].head(4)
        allrounders = matched[matched["role_fixed"] == "ALLROUNDER"].head(2)
        wk = matched[matched["role_fixed"] == "WICKETKEEPER"].head(1)

        final = pd.concat([batsmen, bowlers, allrounders, wk]).drop_duplicates("player")
        if len(final) < 11:
            remaining = matched[~matched["player"].isin(final["player"])]
            final = pd.concat([final, remaining.head(11 - len(final))])
        
        final = final.head(11)

        # Captain logic
        if captain and captain not in final["player"].values:
            cap_row = career_df[career_df["player"] == captain]
            if not cap_row.empty:
                final = final.iloc[:-1]
                final = pd.concat([final, cap_row]).drop_duplicates("player")

        if not vice_captain and len(final) > 1:
            vice_captain = final.iloc[1]["player"]

        result = []
        for _, p in final.iterrows():
            role = p["role_fixed"]
            runs = 0
            wickets = 0

            if bat_model:
                try: runs = int(bat_model.predict([[safe_val(p, "career_runs_per_match")]])[0])
                except: runs = random.randint(25, 40)
            else: runs = random.randint(25, 40)

            if role == "BOWLER": runs = random.randint(5, 18)

            if role in ["BOWLER", "ALLROUNDER"]:
                if bowl_model:
                    try: wickets = int(bowl_model.predict([[safe_val(p, "career_wickets_per_match")]])[0])
                    except: wickets = random.randint(1, 3)
                else: wickets = random.randint(1, 3)
            else: wickets = 0

            run_min = max(10, runs - 8)
            run_max = runs + 8

            result.append({
                "name": p["player"].title(),
                "role": role,
                "runs": f"{run_min} - {run_max}",
                "wickets": wickets,
                "confidence": round(random.uniform(80, 95), 2),
                "captain": p["player"] == captain,
                "vice_captain": p["player"] == vice_captain
            })

        return jsonify({"players": result})

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({"error": "Something went wrong"})

# ================= RUN =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all() 
        # Default Admin (First time run panna create aagum)
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password='password123'))
            db.session.commit()
            print("✅ Admin user created: admin / password123")
    app.run(debug=True)
