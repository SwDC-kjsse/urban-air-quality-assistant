# Problem Statement Alignment — Challenge 6: Urban Air Quality Assistant

**Prompt:** *"Create a GenAI-powered assistant that helps families and communities navigate severe winter smog and urban air pollution. The application should suggest low-emission daily routines, indoor air quality hacks, and sustainable alternatives tailored to their location and lifestyle, while clearly explaining the direct impact of their choices."*

## Direct Alignment Matrix
| Requirement | AeroShield Implementation |
| :--- | :--- |
| **Navigate severe winter smog** | Live Open-Meteo AQI/PM2.5/PM10/NO₂ + 24-hour winter inversion curve + midday safe ventilation window (`13:00–15:30`) or `KEEP SEALED` alert above 300 AQI. |
| **Tailored to location & lifestyle** | Customizes plans by city, household size, children/elderly/asthma sensitivities, commute mode & daily km, home type, cooking fuel (`LPG`, `Induction`, `Solid Fuel`), and budget (`Free`, `Low`, `Pro`). |
| **Low-emission daily routines** | Inversion-aware outdoor scheduling + 3-day commute swaps to transit/carpool + zero-idling guidance. |
| **Indoor air quality hacks** | Budget-matched actions: wet-mopping & draft sealing (`Free`), DIY MERV-13 Corsi-Rosenthal box-fan filter (`Low`), True HEPA H13 bedroom zone (`Pro`), plus kitchen exhaust protocols. |
| **Sustainable alternatives** | Zero-waste winter heating/laundry routines and neighborhood/school carpool pods. |
| **Direct impact explained** | Quantifies baseline vs. projected risk score (`0–100`), combined PM2.5 exposure drop (`%`), weekly/annual CO₂e saved (`kg`), equivalent trees/year, and interactive What-If toggles, paired with Google Gemini briefings and Q&A. |
