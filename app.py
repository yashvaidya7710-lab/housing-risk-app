import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

app = Flask(__name__)

CITY_TIERS = {
    "Mumbai": (18000, 1.35), "Delhi NCR": (14000, 1.25), "Bengaluru": (15000, 1.25),
    "Hyderabad": (11000, 1.05), "Pune": (12000, 1.10), "Chennai": (11000, 1.05),
    "Kolkata": (9000, 0.9), "Ahmedabad": (8500, 0.85), "Tier-2 city": (6500, 0.75),
}
EMPLOYMENT_TYPES = ["Formal salaried", "Self-employed", "Informal/daily wage", "Unemployed"]
SUPPORT_LEVELS = ["Strong", "Moderate", "Weak"]
EDUCATION_LEVELS = ["Graduate+", "Secondary/HSC", "Below secondary"]

FEATURES_NUM = ["monthly_income_inr", "monthly_rent_inr", "rent_to_income_pct", "dependents",
                "tenure_months", "savings_buffer_months", "late_rent_payments_12mo",
                "eviction_notice_5yr", "migrant_worker", "health_shock_12mo"]
FEATURES_CAT = ["city", "employment_type", "social_support", "education"]


def build_training_data(n=6000, seed=42):
    rng = np.random.default_rng(seed)
    cities = list(CITY_TIERS.keys())
    rows = []
    for _ in range(n):
        city = rng.choice(cities)
        base_rent, tier_mult = CITY_TIERS[city]
        employment = rng.choice(EMPLOYMENT_TYPES, p=[0.35, 0.20, 0.35, 0.10])
        income_base = {"Formal salaried": 32000, "Self-employed": 20000,
                       "Informal/daily wage": 13000, "Unemployed": 4000}[employment]
        monthly_income = max(2000, rng.normal(income_base * tier_mult, income_base * 0.35))
        monthly_rent = max(1500, rng.normal(base_rent, base_rent * 0.3))
        dependents = rng.choice([0, 1, 2, 3, 4, 5], p=[0.15, 0.2, 0.25, 0.2, 0.12, 0.08])
        tenure_months = max(1, rng.exponential(30))
        savings_buffer_months = max(0, rng.exponential(1.2))
        late_rent_12mo = rng.poisson(0.6 if employment != "Formal salaried" else 0.15)
        eviction_notice_5yr = rng.choice([0, 1], p=[0.85, 0.15])
        migrant_worker = rng.choice([0, 1], p=[0.6, 0.4])
        health_shock_12mo = rng.choice([0, 1], p=[0.82, 0.18])
        social_support = rng.choice(SUPPORT_LEVELS, p=[0.3, 0.45, 0.25])
        education = rng.choice(EDUCATION_LEVELS, p=[0.2, 0.4, 0.4])
        rows.append(dict(city=city, monthly_income_inr=monthly_income, monthly_rent_inr=monthly_rent,
                          employment_type=employment, dependents=int(dependents),
                          tenure_months=tenure_months, savings_buffer_months=savings_buffer_months,
                          late_rent_payments_12mo=int(late_rent_12mo), eviction_notice_5yr=int(eviction_notice_5yr),
                          migrant_worker=int(migrant_worker), health_shock_12mo=int(health_shock_12mo),
                          social_support=social_support, education=education))
    df = pd.DataFrame(rows)
    df["rent_to_income_pct"] = (df.monthly_rent_inr / df.monthly_income_inr * 100).clip(upper=200)

    support_map = {"Strong": 0, "Moderate": 1, "Weak": 2}
    edu_map = {"Graduate+": 0, "Secondary/HSC": 1, "Below secondary": 2}
    emp_map = {"Formal salaried": 0, "Self-employed": 1, "Informal/daily wage": 2, "Unemployed": 3}

    z = (
        0.045 * (df.rent_to_income_pct - 30)
        + 0.55 * df.employment_type.map(emp_map)
        + 0.30 * df.dependents
        - 0.035 * df.tenure_months.clip(upper=60)
        - 0.9 * df.savings_buffer_months.clip(upper=6)
        + 0.55 * df.late_rent_payments_12mo
        + 1.4 * df.eviction_notice_5yr
        + 0.35 * df.migrant_worker
        + 0.6 * df.health_shock_12mo
        + 0.4 * df.social_support.map(support_map)
        + 0.15 * df.education.map(edu_map)
        - 3.2
    )
    prob_true = 1 / (1 + np.exp(-z))
    df["unstable"] = (rng.uniform(size=n) < prob_true).astype(int)
    return df


def train_model():
    df = build_training_data()
    X = df[FEATURES_NUM + FEATURES_CAT]
    y = df["unstable"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    preprocess = ColumnTransformer([
        ("num", StandardScaler(), FEATURES_NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CAT),
    ])
    pipe = Pipeline([
        ("prep", preprocess),
        ("clf", RandomForestClassifier(n_estimators=400, max_depth=8, min_samples_leaf=5,
                                        class_weight="balanced", random_state=42, n_jobs=-1)),
    ])
    pipe.fit(X_train, y_train)
    proba = pipe.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)

    ohe_names = pipe.named_steps["prep"].named_transformers_["cat"].get_feature_names_out(FEATURES_CAT)
    all_names = FEATURES_NUM + list(ohe_names)
    importances = pipe.named_steps["clf"].feature_importances_
    top_features = sorted(zip(all_names, importances), key=lambda t: -t[1])[:5]

    return pipe, {"AUC": float(auc), "N": len(df)}, top_features


MODEL, METRICS, TOP_FEATURES = train_model()


def band(prob_pct):
    if prob_pct < 20:
        return "Low risk", "cat-lean"
    if prob_pct < 40:
        return "Guarded", "cat-fit"
    if prob_pct < 65:
        return "Elevated", "cat-average"
    return "High risk", "cat-above"


@app.route("/")
def index():
    return render_template("index.html", metrics=METRICS, cities=list(CITY_TIERS.keys()),
                            employment_types=EMPLOYMENT_TYPES, support_levels=SUPPORT_LEVELS,
                            education_levels=EDUCATION_LEVELS)


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(force=True)
        income = float(data["monthly_income_inr"])
        rent = float(data["monthly_rent_inr"])
        if income <= 0:
            return jsonify({"error": "Monthly income must be greater than zero."}), 400

        row = pd.DataFrame([{
            "monthly_income_inr": income,
            "monthly_rent_inr": rent,
            "rent_to_income_pct": min(rent / income * 100, 200),
            "dependents": int(data["dependents"]),
            "tenure_months": float(data["tenure_months"]),
            "savings_buffer_months": float(data["savings_buffer_months"]),
            "late_rent_payments_12mo": int(data["late_rent_payments_12mo"]),
            "eviction_notice_5yr": int(data["eviction_notice_5yr"]),
            "migrant_worker": int(data["migrant_worker"]),
            "health_shock_12mo": int(data["health_shock_12mo"]),
            "city": data["city"],
            "employment_type": data["employment_type"],
            "social_support": data["social_support"],
            "education": data["education"],
        }])

        prob = float(MODEL.predict_proba(row)[0, 1]) * 100
        label, css_class = band(prob)
        rent_pct = row["rent_to_income_pct"].iloc[0]

        return jsonify({
            "probability": round(prob, 1),
            "label": label,
            "css_class": css_class,
            "rent_to_income_pct": round(rent_pct, 1),
            "top_factors": [f for f, _ in TOP_FEATURES],
        })
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Check the values you entered ({e})."}), 400


if __name__ == "__main__":
    app.run(debug=True)