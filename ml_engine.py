import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, confusion_matrix, roc_curve
from data_generator import generate_hospital_data, save_dataset
import os

class ReadmissionPredictor:
    def __init__(self, data_path=None):
        self.data_path = data_path
        self.model = None
        self.feature_names = []
        self.feature_importances = {}
        self.metrics = {}
        self.roc_data = {}
        self.df = None
        
    def load_or_generate_data(self):
        if self.data_path and os.path.exists(self.data_path):
            self.df = pd.read_csv(self.data_path)
        else:
            self.df = generate_hospital_data()
            if self.data_path:
                self.df.to_csv(self.data_path, index=False)
        return self.df

    def train_model(self):
        if self.df is None:
            self.load_or_generate_data()
            
        # Prepare features & target
        feature_cols = [
            'age', 'length_of_stay', 'prior_admissions_12m', 'emergency_visits_6m',
            'num_medications', 'has_diabetes', 'has_hypertension', 'has_heart_disease',
            'has_ckd', 'abnormal_labs'
        ]
        
        # Categorical encoding
        df_encoded = pd.get_dummies(
            self.df[feature_cols + ['gender', 'department', 'discharge_destination']], 
            columns=['gender', 'department', 'discharge_destination'],
            drop_first=True
        )
        
        X = df_encoded
        y = self.df['readmitted_30d']
        
        self.feature_names = list(X.columns)
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        
        # Train Random Forest
        self.model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Predict & Evaluate
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        # Calculate ROC Curve points
        fpr, tpr, thresholds = roc_curve(y_test, y_prob)
        # Downsample ROC points for fast JS rendering
        step = max(1, len(fpr) // 20)
        self.roc_data = {
            'fpr': np.round(fpr[::step], 3).tolist(),
            'tpr': np.round(tpr[::step], 3).tolist()
        }
        
        cm = confusion_matrix(y_test, y_pred)
        
        self.metrics = {
            'accuracy': float(np.round(accuracy_score(y_test, y_pred), 3)),
            'roc_auc': float(np.round(roc_auc_score(y_test, y_prob), 3)),
            'precision': float(np.round(precision_score(y_test, y_pred), 3)),
            'recall': float(np.round(recall_score(y_test, y_pred), 3)),
            'confusion_matrix': cm.tolist()
        }
        
        # Feature importances
        importances = self.model.feature_importances_
        sorted_indices = np.argsort(importances)[::-1]
        
        self.feature_importances = {
            self.feature_names[i]: float(np.round(importances[i], 4))
            for i in sorted_indices
        }
        
        return self.metrics

    def predict_patient_risk(self, patient_dict):
        """
        Takes patient dictionary, processes features, and returns prediction probability + risk details.
        """
        if self.model is None:
            self.train_model()
            
        # Build DataFrame for single input
        row = {col: 0 for col in self.feature_names}
        
        # Standard features
        for key in ['age', 'length_of_stay', 'prior_admissions_12m', 'emergency_visits_6m',
                    'num_medications', 'has_diabetes', 'has_hypertension', 'has_heart_disease',
                    'has_ckd', 'abnormal_labs']:
            if key in patient_dict:
                row[key] = float(patient_dict[key])
                
        # One-hot encoded matches
        gender = patient_dict.get('gender', 'Female')
        if f"gender_{gender}" in row:
            row[f"gender_{gender}"] = 1
            
        dept = patient_dict.get('department', 'General Ward')
        if f"department_{dept}" in row:
            row[f"department_{dept}"] = 1
            
        dest = patient_dict.get('discharge_destination', 'Home')
        if f"discharge_destination_{dest}" in row:
            row[f"discharge_destination_{dest}"] = 1
            
        input_df = pd.DataFrame([row])[self.feature_names]
        
        prob = float(self.model.predict_proba(input_df)[0][1])
        prob_pct = int(np.round(prob * 100))
        
        if prob >= 0.65:
            risk_level = "High Risk"
            risk_color = "red"
        elif prob >= 0.35:
            risk_level = "Moderate Risk"
            risk_color = "amber"
        else:
            risk_level = "Low Risk"
            risk_color = "green"
            
        # Determine specific contributing factors
        factors = []
        if float(patient_dict.get('prior_admissions_12m', 0)) >= 2:
            factors.append("Frequent Prior Admissions (>=2 in past year)")
        if float(patient_dict.get('emergency_visits_6m', 0)) >= 2:
            factors.append("Multiple Recent Emergency Visits")
        if float(patient_dict.get('has_ckd', 0)) == 1:
            factors.append("Chronic Kidney Disease (High Comorbidity Risk)")
        if float(patient_dict.get('has_heart_disease', 0)) == 1:
            factors.append("Cardiac Disease History")
        if float(patient_dict.get('abnormal_labs', 0)) == 1:
            factors.append("Abnormal Discharge Lab Flags")
        if float(patient_dict.get('length_of_stay', 0)) >= 7:
            factors.append(f"Extended Length of Stay ({patient_dict.get('length_of_stay')} days)")
        if float(patient_dict.get('age', 0)) >= 70:
            factors.append("Advanced Patient Age (>=70)")

        if not factors:
            factors.append("Baseline clinical indicator distribution")

        # Recommendations
        recommendations = []
        if risk_level == "High Risk":
            recommendations.append("Assign dedicated Home Health Care nurse for post-discharge monitoring.")
            recommendations.append("Schedule obligatory 48-hour tele-health check-in.")
            recommendations.append("Perform full medication reconciliation before discharge.")
        elif risk_level == "Moderate Risk":
            recommendations.append("Schedule 7-day primary care follow-up visit.")
            recommendations.append("Provide targeted disease management education leaflets.")
        else:
            recommendations.append("Standard post-discharge instructions & standard 14-day follow-up.")

        return {
            'probability': prob,
            'probability_pct': prob_pct,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'contributing_factors': factors,
            'recommendations': recommendations
        }

if __name__ == "__main__":
    predictor = ReadmissionPredictor()
    metrics = predictor.train_model()
    print("Model Training Complete. Metrics:", metrics)
    print("\nTop 5 Features:", list(predictor.feature_importances.items())[:5])
