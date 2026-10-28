# 🥗 BMI & Daily Calorie Calculator

A simple Streamlit app where an adult enters their age, sex, weight, height and
activity level, and the app shows:

- **BMI** and its category (WHO adult ranges)
- A **healthy weight range** for their height
- **Daily calories** needed to maintain, lose, or gain weight gradually
- A short, friendly **AI explanation** with general tips (powered by Groq)

> ⚠️ This app gives general estimates, not medical advice. BMI does not measure
> muscle or body fat. Talk to a doctor or registered dietitian for personal advice.

## How it works

| Step | Method |
|------|--------|
| BMI | weight (kg) ÷ height (m)² |
| BMR | Mifflin-St Jeor equation |
| Maintenance calories | BMR × activity multiplier (1.2 – 1.9) |
| Goal calories | about 15% below (lose) or 10% above (gain) maintenance, never below 1,500 kcal (men) / 1,200 kcal (women) |

All numbers are calculated in Python. The Groq model only explains the results,
so the figures are never invented by the AI.

## Run locally

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
pip install -r requirements.txt
```

Create the file `.streamlit/secrets.toml` (do **not** commit it):

```toml
GROQ_API_KEY = "your_groq_api_key_here"
```

Then start the app:

```bash
streamlit run app.py
```

Get a free API key at <https://console.groq.com/keys>.

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to <https://share.streamlit.io> and click **Create app**.
3. Select your repo, branch `main`, and main file `app.py`.
4. Open **Advanced settings → Secrets** and paste:
   ```toml
   GROQ_API_KEY = "your_groq_api_key_here"
   ```
5. Click **Deploy**.

## Changing the AI model

The default model is `openai/gpt-oss-120b`. Groq retires models from time to
time. To switch without editing code, add this to your secrets:

```toml
GROQ_MODEL = "model-name-from-console.groq.com/docs/models"
```

## Files

- `app.py` – the Streamlit app
- `requirements.txt` – Python dependencies
- `README.md` – this file
