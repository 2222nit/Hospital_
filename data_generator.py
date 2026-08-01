import os
import numpy as np
import pandas as pd


def generate_hospital_data(n_samples=1200, random_state=42):
    np.random.seed(random_state)
    patient_ids = [f"PAT-{1000 + i}" for i in range(n_samples)]
    ages = np.random.randint(18, 90, size=n_samples)
    genders = np.random.choice(['Male', 'Female'], size=n_samples, p=[0.48, 0.52])
    departments = np.random.choice(['General Ward', 'ICU', 'Emergency', 'Surgery', 'Cardiology'], size=n_samples, p=[0.35, 0.15, 0.25, 0.15, 0.10])
    los_base = {'General Ward': (3, 2), 'ICU': (8, 4), 'Emergency': (1, 1), 'Surgery': (5, 3), 'Cardiology': (6, 3)}
    length_of_stay = np.array([int(np.clip(np.random.normal(*los_base[d]), 1, 30)) for d in departments])
    prior_admissions = np.clip(np.random.poisson(lam=1.2, size=n_samples), 0, 10)
    emergency_visits_6m = np.clip(np.random.poisson(lam=0.8, size=n_samples), 0, 8)
    num_medications = np.random.randint(1, 22, size=n_samples)
    has_diabetes = np.random.binomial(1, p=0.28, size=n_samples)
    has_hypertension = np.random.binomial(1, p=0.45, size=n_samples)
    has_heart_disease = np.random.binomial(1, p=0.22, size=n_samples)
    has_ckd = np.random.binomial(1, p=0.15, size=n_samples)
    abnormal_labs = np.random.binomial(1, p=0.32, size=n_samples)
    discharge_destinations = np.random.choice(['Home', 'Home Health Care', 'Skilled Nursing Facility'], size=n_samples, p=[0.60, 0.25, 0.15])
    log_odds = (-3.2 + 0.025 * (ages - 50) + 0.35 * prior_admissions + 0.40 * emergency_visits_6m + 0.05 * length_of_stay + 0.45 * has_diabetes + 0.30 * has_hypertension + 0.60 * has_heart_disease + 0.70 * has_ckd + 0.50 * abnormal_labs + 0.35 * (discharge_destinations == 'Skilled Nursing Facility').astype(int) + 0.20 * (departments == 'ICU').astype(int) + np.random.normal(0, 0.4, size=n_samples))
    probabilities = 1 / (1 + np.exp(-log_odds))
    readmitted_30d = (probabilities >= 0.42).astype(int)
    return pd.DataFrame({'patient_id': patient_ids, 'age': ages, 'gender': genders, 'department': departments, 'length_of_stay': length_of_stay, 'prior_admissions_12m': prior_admissions, 'emergency_visits_6m': emergency_visits_6m, 'num_medications': num_medications, 'has_diabetes': has_diabetes, 'has_hypertension': has_hypertension, 'has_heart_disease': has_heart_disease, 'has_ckd': has_ckd, 'abnormal_labs': abnormal_labs, 'discharge_destination': discharge_destinations, 'readmission_prob_true': np.round(probabilities, 3), 'readmitted_30d': readmitted_30d})


def save_dataset(filepath=None):
    if filepath is None:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hospital_data.csv')
    df = generate_hospital_data()
    df.to_csv(filepath, index=False)
    print(f'Generated dataset with {len(df)} records at {filepath}')
    return df


if __name__ == '__main__':
    save_dataset()
