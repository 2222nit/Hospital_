from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import os
from data_generator import generate_hospital_data, save_dataset
from ml_engine import ReadmissionPredictor

app = Flask(__name__, static_folder='static', template_folder='templates')

DATA_PATH = os.path.join(os.path.dirname(__file__), 'hospital_data.csv')
predictor = ReadmissionPredictor(data_path=DATA_PATH)

# Ensure data and model are initialized at startup
predictor.load_or_generate_data()
predictor.train_model()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/overview', methods=['GET'])
def get_overview():
    df = predictor.df
    total_patients = len(df)
    readmitted_count = int(df['readmitted_30d'].sum())
    readmission_rate = float(np.round((readmitted_count / total_patients) * 100, 1))
    
    avg_los = float(np.round(df['length_of_stay'].mean(), 1))
    
    # Calculate bed occupancy (synthetic total capacity: 600 beds)
    total_beds = 600
    current_occupied = int(df['length_of_stay'].apply(lambda x: min(x, 10)).sum() / 7) + 380
    current_occupied = min(total_beds, max(300, current_occupied))
    occupancy_pct = float(np.round((current_occupied / total_beds) * 100, 1))
    
    # High risk patients count
    high_risk_count = int((df['readmission_prob_true'] >= 0.55).sum())
    
    return jsonify({
        'total_patients': total_patients,
        'readmission_rate': readmission_rate,
        'readmitted_count': readmitted_count,
        'avg_length_of_stay': avg_los,
        'total_beds': total_beds,
        'occupied_beds': current_occupied,
        'occupancy_pct': occupancy_pct,
        'high_risk_patients_count': high_risk_count
    })

@app.route('/api/utilization', methods=['GET'])
def get_utilization():
    df = predictor.df
    dept_stats = []
    
    # Capacity estimates per department
    dept_capacities = {
        'General Ward': 220,
        'ICU': 50,
        'Emergency': 80,
        'Surgery': 100,
        'Cardiology': 70
    }
    
    for dept, cap in dept_capacities.items():
        dept_df = df[df['department'] == dept]
        patient_count = len(dept_df)
        avg_los = float(np.round(dept_df['length_of_stay'].mean(), 1)) if patient_count > 0 else 0
        readm_pct = float(np.round((dept_df['readmitted_30d'].mean() * 100), 1)) if patient_count > 0 else 0
        
        # Occupancy estimate
        occupied = min(cap, int(patient_count * 0.45 + (15 if dept == 'ICU' else 25)))
        occ_pct = float(np.round((occupied / cap) * 100, 1))
        
        dept_stats.append({
            'department': dept,
            'total_patients': patient_count,
            'capacity': cap,
            'occupied': occupied,
            'occupancy_pct': occ_pct,
            'avg_los': avg_los,
            'readmission_rate': readm_pct
        })
        
    # Generate 30-day timeline trend data for chart
    timeline_days = [f"Day {i+1}" for i in range(30)]
    np.random.seed(10)
    general_trend = (np.sin(np.linspace(0, 3*np.pi, 30)) * 12 + 78 + np.random.normal(0, 3, 30)).clip(60, 95).round(1).tolist()
    icu_trend = (np.cos(np.linspace(0, 2*np.pi, 30)) * 8 + 84 + np.random.normal(0, 2, 30)).clip(70, 98).round(1).tolist()
    er_trend = (np.sin(np.linspace(0, 4*np.pi, 30)) * 15 + 72 + np.random.normal(0, 4, 30)).clip(55, 95).round(1).tolist()
    
    return jsonify({
        'departments': dept_stats,
        'timeline': {
            'days': timeline_days,
            'general_ward': general_trend,
            'icu': icu_trend,
            'emergency': er_trend
        }
    })

@app.route('/api/patients', methods=['GET'])
def get_patients():
    df = predictor.df
    search = request.args.get('search', '').lower()
    dept = request.args.get('department', '')
    risk_level = request.args.get('risk_level', '')
    
    records = []
    for idx, row in df.iterrows():
        prob = row['readmission_prob_true']
        if prob >= 0.60:
            r_level = "High"
        elif prob >= 0.35:
            r_level = "Moderate"
        else:
            r_level = "Low"
            
        p_data = {
            'patient_id': row['patient_id'],
            'age': int(row['age']),
            'gender': row['gender'],
            'department': row['department'],
            'length_of_stay': int(row['length_of_stay']),
            'prior_admissions_12m': int(row['prior_admissions_12m']),
            'emergency_visits_6m': int(row['emergency_visits_6m']),
            'discharge_destination': row['discharge_destination'],
            'readmission_prob': float(row['readmission_prob_true']),
            'readmission_pct': int(np.round(row['readmission_prob_true'] * 100)),
            'risk_level': r_level,
            'readmitted_30d': int(row['readmitted_30d'])
        }
        
        # Filtering logic
        if search and search not in p_data['patient_id'].lower() and search not in p_data['department'].lower():
            continue
        if dept and dept != 'All' and p_data['department'] != dept:
            continue
        if risk_level and risk_level != 'All' and p_data['risk_level'] != risk_level:
            continue
            
        records.append(p_data)
        if len(records) >= 150: # Limit returned rows for UX speed
            break
            
    return jsonify({'patients': records, 'total_count': len(records)})

@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.json or {}
    result = predictor.predict_patient_risk(data)
    return jsonify(result)

@app.route('/api/model-stats', methods=['GET'])
def get_model_stats():
    return jsonify({
        'metrics': predictor.metrics,
        'feature_importances': predictor.feature_importances,
        'roc_curve': predictor.roc_data
    })

@app.route('/api/regenerate', methods=['POST'])
def regenerate_data():
    predictor.df = save_dataset(DATA_PATH)
    metrics = predictor.train_model()
    return jsonify({'status': 'success', 'message': 'Dataset regenerated and model retrained.', 'metrics': metrics})

if __name__ == '__main__':
    print("Starting Hospital Analytics Flask Server on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
