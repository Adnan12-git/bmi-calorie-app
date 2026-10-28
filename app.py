"""BMI & Daily Calorie Calculator.

Streamlit UI + Groq AI model.

The numbers (BMI, BMR, calories) are calculated with standard formulas in
plain Python, so they are always consistent. The Groq model is only used to
write a short, friendly explanation and general lifestyle tips from those
numbers.
"""

import os

import streamlit as st

try:
    from groq import Groq
except ImportError:  # lets the calculator still work if groq is missing
    Groq = None

# Groq retires models from time to time. You can override this without
# touching the code by setting GROQ_MODEL in Streamlit secrets or env vars.
DEFAULT_MODEL = "openai/gpt-oss-120b"

ACTIVITY_LEVELS = {
    "Sedentary (little or no exercise)": 1.2,
    "Light (exercise 1-3 days/week)": 1.375,
    "Moderate (exercise 3-5 days/week)": 1.55,
    "Active (hard exercise 6-7 days/week)": 1.725,
    "Very active (physical job or 2x training/day)": 1.9,
}

GOALS = [
    "Maintain my weight",
    "Lose weight gradually",
    "Gain weight gradually",
]

MIN_CALORIES = {"Male": 1500, "Female": 1200}


# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------
def lbs_to_kg(lbs: float) -> float:
    return lbs * 0.45359237


def feet_inches_to_cm(feet: float, inches: float) -> float:
    return (feet * 12 + inches) * 2.54


def kg_to_lbs(kg: float) -> float:
    return kg / 0.45359237


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return weight_kg / (height_m ** 2)


def bmi_category(bmi: float) -> str:
    """WHO adult BMI categories."""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal weight"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def healthy_weight_range(height_cm: float) -> tuple[float, float]:
    """Weight range (kg) for a BMI between 18.5 and 24.9."""
    height_m = height_cm / 100
    return 18.5 * height_m ** 2, 24.9 * height_m ** 2


def calculate_bmr(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """Mifflin-St Jeor equation (kcal/day at rest)."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "Male" else base - 161


def calculate_tdee(bmr: float, activity_multiplier: float) -> float:
    return bmr * activity_multiplier


def calorie_target(tdee: float, goal: str, sex: str, bmi: float) -> tuple[int, str]:
    """Return (daily calories, short note) for the chosen goal.

    Safety rules:
    - never go below a minimum daily intake
    - never suggest a deficit to someone who is underweight
    """
    note = ""
    if goal == "Lose weight gradually":
        if bmi < 18.5:
            target = tdee
            goal = "Maintain my weight"
            note = (
                "Your BMI is in the underweight range, so a calorie deficit is "
                "not recommended. Showing maintenance calories instead."
            )
        else:
            target = tdee * 0.85
    elif goal == "Gain weight gradually":
        target = tdee * 1.10
    else:
        target = tdee

    floor = MIN_CALORIES[sex]
    if target < floor:
        target = floor
        note = (
            f"The target was raised to {floor} kcal, which is the lowest "
            "intake generally considered safe without medical supervision."
        )

    return int(round(target / 10.0) * 10), note


# ---------------------------------------------------------------------------
# AI (Groq)
# ---------------------------------------------------------------------------
def _get_setting(name: str, default: str = "") -> str:
    """Read from Streamlit secrets first, then environment variables."""
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass  # no secrets file present
    return os.environ.get(name, default)


def get_ai_advice(data: dict) -> str:
    api_key = _get_setting("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it in Streamlit secrets or as an "
            "environment variable."
        )
    if Groq is None:
        raise RuntimeError("The 'groq' package is not installed.")

    client = Groq(api_key=api_key)
    model = _get_setting("GROQ_MODEL", DEFAULT_MODEL)

    system_prompt = (
        "You are a friendly health-and-nutrition information assistant. "
        "You are given numbers that were already calculated: use them exactly "
        "as given and never recalculate or change them. Write a short, "
        "encouraging explanation in plain language (about 150-220 words) with "
        "these parts: 1) what the BMI result means, including that BMI is only "
        "a screening tool and does not measure body fat or muscle, 2) what the "
        "calorie number means, 3) three practical, balanced tips for food and "
        "activity. Do not diagnose any condition, do not recommend extreme "
        "diets, fasting, or supplements, and end with one sentence suggesting "
        "they talk to a doctor or registered dietitian for personal advice."
    )

    user_prompt = (
        f"Age: {data['age']}\n"
        f"Sex: {data['sex']}\n"
        f"Height: {data['height_cm']:.0f} cm\n"
        f"Weight: {data['weight_kg']:.1f} kg\n"
        f"BMI: {data['bmi']:.1f} ({data['category']})\n"
        f"Activity level: {data['activity']}\n"
        f"Goal: {data['goal']}\n"
        f"Estimated maintenance calories: {data['tdee']:.0f} kcal/day\n"
        f"Suggested daily calories for the goal: {data['target']} kcal/day"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        max_completion_tokens=2000,  # reasoning models also spend tokens thinking
    )
    text = response.choices[0].message.content
    if not text or not text.strip():
        raise RuntimeError("The AI model returned an empty response.")
    return text.strip()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="BMI & Calorie Calculator", page_icon="🥗")
    st.title("🥗 BMI & Daily Calorie Calculator")
    st.caption(
        "Enter your details to get your BMI and an estimate of the calories "
        "you need each day. For adults 18 and over."
    )

    units = st.radio("Units", ["Metric (kg, cm)", "Imperial (lb, ft/in)"], horizontal=True)
    metric = units.startswith("Metric")

    with st.form("details_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age (years)", min_value=18, max_value=100, value=25, step=1)
        with col2:
            sex = st.selectbox(
                "Sex (used in the formula)",
                ["Male", "Female"],
                help="The calorie formula uses sex assigned at birth.",
            )

        if metric:
            col3, col4 = st.columns(2)
            with col3:
                weight_in = st.number_input(
                    "Weight (kg)", min_value=30.0, max_value=300.0, value=70.0, step=0.5
                )
            with col4:
                height_in = st.number_input(
                    "Height (cm)", min_value=120.0, max_value=230.0, value=170.0, step=0.5
                )
            weight_kg = weight_in
            height_cm = height_in
        else:
            col3, col4, col5 = st.columns(3)
            with col3:
                weight_lbs = st.number_input(
                    "Weight (lb)", min_value=66.0, max_value=660.0, value=154.0, step=1.0
                )
            with col4:
                feet = st.number_input("Height (ft)", min_value=3, max_value=7, value=5, step=1)
            with col5:
                inches = st.number_input(
                    "Height (in)", min_value=0.0, max_value=11.9, value=7.0, step=0.5
                )
            weight_kg = lbs_to_kg(weight_lbs)
            height_cm = feet_inches_to_cm(feet, inches)

        activity = st.selectbox("Activity level", list(ACTIVITY_LEVELS.keys()), index=1)
        goal = st.selectbox("Goal", GOALS)
        submitted = st.form_submit_button("Calculate", type="primary")

    if not submitted:
        return

    if not (120 <= height_cm <= 230):
        st.error("Please enter a height between about 4 ft (120 cm) and 7 ft 7 in (230 cm).")
        return

    # --- calculations ---
    bmi = calculate_bmi(weight_kg, height_cm)
    category = bmi_category(bmi)
    low_kg, high_kg = healthy_weight_range(height_cm)
    bmr = calculate_bmr(sex, weight_kg, height_cm, int(age))
    tdee = calculate_tdee(bmr, ACTIVITY_LEVELS[activity])
    target, note = calorie_target(tdee, goal, sex, bmi)

    # --- results ---
    st.subheader("Your results")
    m1, m2, m3 = st.columns(3)
    m1.metric("BMI", f"{bmi:.1f}")
    m1.caption(f"Category: **{category}**")
    m2.metric("Maintenance calories", f"{tdee:,.0f} kcal/day")
    m3.metric("Calories for your goal", f"{target:,} kcal/day")

    if metric:
        range_text = f"{low_kg:.1f} - {high_kg:.1f} kg"
    else:
        range_text = f"{kg_to_lbs(low_kg):.0f} - {kg_to_lbs(high_kg):.0f} lb"
    st.info(f"A BMI between 18.5 and 24.9 for your height is a weight of about **{range_text}**.")

    if note:
        st.warning(note)

    with st.expander("How these numbers are calculated"):
        st.markdown(
            "- **BMI** = weight (kg) ÷ height (m)²\n"
            "- **BMR** (calories burned at rest) uses the Mifflin-St Jeor equation: "
            f"about **{bmr:,.0f} kcal/day** for you\n"
            "- **Maintenance calories** = BMR × activity multiplier\n"
            "- **Weight loss** targets about 15% below maintenance, **weight gain** about "
            "10% above, never below a safe minimum"
        )

    # --- AI explanation ---
    st.subheader("AI insights")
    data = {
        "age": int(age),
        "sex": sex,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "bmi": bmi,
        "category": category,
        "activity": activity,
        "goal": goal,
        "tdee": tdee,
        "target": target,
    }
    with st.spinner("Asking the AI for a personalised explanation..."):
        try:
            st.markdown(get_ai_advice(data))
        except Exception as exc:  # show a friendly message instead of a crash
            st.error(f"Could not get AI insights: {exc}")
            st.caption("Your BMI and calorie results above are still valid.")

    st.caption(
        "⚠️ This tool gives general estimates, not medical advice. BMI does not "
        "account for muscle mass, age, or body composition. Talk to a doctor or "
        "registered dietitian before making big changes to your diet."
    )


if __name__ == "__main__":
    main()
