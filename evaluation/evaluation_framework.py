"""
MakFleet Evaluation and Benchmarking Framework
Comprehensive evaluation of AI models, system performance, and business metrics
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json
import time
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, mean_squared_error, mean_absolute_error
)
import psutil
import os


@dataclass
class ModelEvaluationMetrics:
    """Comprehensive model evaluation metrics"""
    model_name: str
    dataset: str
    timestamp: datetime
    
    # Classification metrics
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    auc_roc: Optional[float] = None
    
    # Regression metrics
    mse: Optional[float] = None
    mae: Optional[float] = None
    rmse: Optional[float] = None
    
    # Custom spatio-temporal metrics
    spatial_accuracy: Optional[float] = None
    temporal_consistency: Optional[float] = None
    anomaly_detection_rate: Optional[float] = None
    
    # Performance metrics
    inference_time_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    model_size_mb: Optional[float] = None
    
    # Business metrics
    false_positive_cost: Optional[float] = None
    false_negative_cost: Optional[float] = None
    business_value_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_name': self.model_name,
            'dataset': self.dataset,
            'timestamp': self.timestamp.isoformat(),
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'auc_roc': self.auc_roc,
            'mse': self.mse,
            'mae': self.mae,
            'rmse': self.rmse,
            'spatial_accuracy': self.spatial_accuracy,
            'temporal_consistency': self.temporal_consistency,
            'anomaly_detection_rate': self.anomaly_detection_rate,
            'inference_time_ms': self.inference_time_ms,
            'memory_usage_mb': self.memory_usage_mb,
            'model_size_mb': self.model_size_mb,
            'false_positive_cost': self.false_positive_cost,
            'false_negative_cost': self.false_negative_cost,
            'business_value_score': self.business_value_score
        }


@dataclass
class SystemPerformanceMetrics:
    """System-wide performance metrics"""
    timestamp: datetime
    uptime_seconds: float
    cpu_usage_percent: float
    memory_usage_mb: float
    disk_usage_gb: float
    network_throughput_mbps: float
    
    # Application-specific metrics
    active_connections: int
    request_rate_per_second: float
    average_response_time_ms: float
    error_rate_percent: float
    
    # Data processing metrics
    telemetry_processed_per_second: float
    events_detected_per_minute: float
    anomalies_detected_per_hour: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'uptime_seconds': self.uptime_seconds,
            'cpu_usage_percent': self.cpu_usage_percent,
            'memory_usage_mb': self.memory_usage_mb,
            'disk_usage_gb': self.disk_usage_gb,
            'network_throughput_mbps': self.network_throughput_mbps,
            'active_connections': self.active_connections,
            'request_rate_per_second': self.request_rate_per_second,
            'average_response_time_ms': self.average_response_time_ms,
            'error_rate_percent': self.error_rate_percent,
            'telemetry_processed_per_second': self.telemetry_processed_per_second,
            'events_detected_per_minute': self.events_detected_per_minute,
            'anomalies_detected_per_hour': self.anomalies_detected_per_hour
        }


class ModelEvaluator:
    """Evaluates AI models with comprehensive metrics"""
    
    def __init__(self):
        self.baseline_models = {
            'random_forest': 'Traditional ML baseline',
            'xgboost': 'Gradient boosting baseline',
            'st_gnn_ours': 'Our ST-GNN model'
        }
    
    def evaluate_st_gnn(self, model, test_data: pd.DataFrame,
                       test_labels: np.ndarray) -> ModelEvaluationMetrics:
        """Evaluate ST-GNN model performance"""
        start_time = time.time()
        
        # Get predictions
        predictions, anomaly_scores = model(test_data)
        
        inference_time = (time.time() - start_time) * 1000  # ms
        
        # Convert to numpy for metrics
        pred_numpy = predictions.detach().numpy() if hasattr(predictions, 'detach') else predictions
        anomaly_numpy = anomaly_scores.detach().numpy() if hasattr(anomaly_scores, 'detach') else anomaly_scores
        
        # Calculate metrics
        metrics = ModelEvaluationMetrics(
            model_name='ST-GNN',
            dataset='bodaboda_telemetry',
            timestamp=datetime.utcnow()
        )
        
        # Anomaly detection metrics (binary classification)
        if len(test_labels.shape) > 1:
            # Multi-class or regression task
            metrics.mse = mean_squared_error(test_labels.flatten(), pred_numpy.flatten())
            metrics.mae = mean_absolute_error(test_labels.flatten(), pred_numpy.flatten())
            metrics.rmse = np.sqrt(metrics.mse)
        else:
            # Binary classification for anomaly detection
            pred_binary = (anomaly_numpy > 0.5).astype(int).flatten()
            true_binary = test_labels.astype(int).flatten()
            
            metrics.accuracy = accuracy_score(true_binary, pred_binary)
            metrics.precision = precision_score(true_binary, pred_binary, zero_division=0)
            metrics.recall = recall_score(true_binary, pred_binary, zero_division=0)
            metrics.f1_score = f1_score(true_binary, pred_binary, zero_division=0)
            
            try:
                metrics.auc_roc = roc_auc_score(true_binary, anomaly_numpy.flatten())
            except:
                metrics.auc_roc = None
        
        # Custom spatio-temporal metrics
        metrics.spatial_accuracy = self._calculate_spatial_accuracy(test_data, pred_numpy)
        metrics.temporal_consistency = self._calculate_temporal_consistency(test_data, pred_numpy)
        metrics.anomaly_detection_rate = np.mean(anomaly_numpy > 0.5)
        
        # Performance metrics
        metrics.inference_time_ms = inference_time
        metrics.memory_usage_mb = self._get_memory_usage()
        metrics.model_size_mb = self._get_model_size(model)
        
        # Business value calculation
        metrics.business_value_score = self._calculate_business_value(metrics)
        
        return metrics
    
    def evaluate_baseline_models(self, models: Dict[str, Any],
                               test_data: pd.DataFrame,
                               test_labels: np.ndarray) -> List[ModelEvaluationMetrics]:
        """Evaluate baseline models for comparison"""
        results = []
        
        for model_name, model in models.items():
            try:
                start_time = time.time()
                predictions = model.predict(test_data)
                inference_time = (time.time() - start_time) * 1000
                
                metrics = ModelEvaluationMetrics(
                    model_name=model_name,
                    dataset='bodaboda_telemetry',
                    timestamp=datetime.utcnow(),
                    inference_time_ms=inference_time
                )
                
                if len(test_labels.shape) == 1:
                    # Classification
                    pred_binary = (predictions > 0.5).astype(int)
                    true_binary = test_labels.astype(int)
                    
                    metrics.accuracy = accuracy_score(true_binary, pred_binary)
                    metrics.precision = precision_score(true_binary, pred_binary, zero_division=0)
                    metrics.recall = recall_score(true_binary, pred_binary, zero_division=0)
                    metrics.f1_score = f1_score(true_binary, pred_binary, zero_division=0)
                    
                    try:
                        metrics.auc_roc = roc_auc_score(true_binary, predictions)
                    except:
                        metrics.auc_roc = None
                else:
                    # Regression
                    metrics.mse = mean_squared_error(test_labels, predictions)
                    metrics.mae = mean_absolute_error(test_labels, predictions)
                    metrics.rmse = np.sqrt(metrics.mse)
                
                results.append(metrics)
                
            except Exception as e:
                print(f"Error evaluating {model_name}: {e}")
                continue
        
        return results
    
    def _calculate_spatial_accuracy(self, test_data: pd.DataFrame, predictions: np.ndarray) -> float:
        """Calculate spatial accuracy for location predictions"""
        # Simplified spatial accuracy based on coordinate predictions
        if 'latitude' in test_data.columns and 'longitude' in test_data.columns:
            # For trajectory prediction tasks
            lat_pred = predictions[:, :, 2] if len(predictions.shape) > 2 else predictions[:, 2]
            lon_pred = predictions[:, :, 3] if len(predictions.shape) > 2 else predictions[:, 3]
            
            lat_true = test_data['latitude'].values
            lon_true = test_data['longitude'].values
            
            # Calculate mean distance error in meters
            distances = []
            for i in range(min(len(lat_pred), len(lat_true))):
                dist = self._haversine_distance(
                    lat_true[i], lon_true[i],
                    lat_pred[i], lon_pred[i]
                )
                distances.append(dist)
            
            return np.mean(distances) if distances else 0.0
        
        return 0.0
    
    def _calculate_temporal_consistency(self, test_data: pd.DataFrame, predictions: np.ndarray) -> float:
        """Calculate temporal consistency of predictions"""
        # Check if predictions maintain temporal ordering
        if len(predictions.shape) > 2:  # Sequence predictions
            # Check speed predictions maintain reasonable ranges
            speed_pred = predictions[:, :, 0]  # Speed predictions
            speed_changes = np.abs(np.diff(speed_pred, axis=1))
            
            # Reasonable speed changes (< 10 m/s² acceleration)
            reasonable_changes = speed_changes < 10.0
            consistency = np.mean(reasonable_changes)
            
            return float(consistency)
        
        return 0.8  # Default moderate consistency
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def _get_model_size(self, model) -> float:
        """Get model size in MB"""
        if hasattr(model, 'parameters'):
            param_size = sum(p.numel() * p.element_size() for p in model.parameters())
            return param_size / 1024 / 1024
        return 0.0
    
    def _calculate_business_value(self, metrics: ModelEvaluationMetrics) -> float:
        """Calculate business value score"""
        if metrics.precision is not None and metrics.recall is not None:
            # Business value considers both precision (avoiding false alarms) and recall (catching real issues)
            # False positive cost: unnecessary interventions
            # False negative cost: missed safety issues
            fp_cost = 1 - metrics.precision  # Cost of false alarms
            fn_cost = 1 - metrics.recall     # Cost of missed detections
            
            # Weighted business value (prioritize recall for safety)
            business_value = 1 - (0.3 * fp_cost + 0.7 * fn_cost)
            return max(0.0, min(1.0, business_value))
        
        return 0.5  # Neutral score
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate Haversine distance in meters"""
        R = 6371000
        phi1, phi2 = np.radians([lat1, lat2])
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        
        a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(np.sqrt(1-a)))
        
        return R * c


class SystemBenchmarker:
    """Benchmarks overall system performance"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.performance_history = []
    
    def collect_system_metrics(self) -> SystemPerformanceMetrics:
        """Collect current system performance metrics"""
        metrics = SystemPerformanceMetrics(
            timestamp=datetime.utcnow(),
            uptime_seconds=(datetime.utcnow() - self.start_time).total_seconds(),
            cpu_usage_percent=psutil.cpu_percent(),
            memory_usage_mb=psutil.virtual_memory().used / 1024 / 1024,
            disk_usage_gb=psutil.disk_usage('/').used / 1024 / 1024 / 1024,
            network_throughput_mbps=self._get_network_throughput(),
            active_connections=0,  # Would need application-specific tracking
            request_rate_per_second=0.0,  # Would need request tracking
            average_response_time_ms=0.0,  # Would need response time tracking
            error_rate_percent=0.0,  # Would need error tracking
            telemetry_processed_per_second=0.0,  # Would need telemetry processing tracking
            events_detected_per_minute=0.0,  # Would need event detection tracking
            anomalies_detected_per_hour=0.0  # Would need anomaly detection tracking
        )
        
        self.performance_history.append(metrics)
        return metrics
    
    def _get_network_throughput(self) -> float:
        """Get network throughput in Mbps"""
        try:
            net_io = psutil.net_io_counters()
            # Simplified calculation - would need time-based measurement for accuracy
            return (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024
        except:
            return 0.0
    
    def run_load_test(self, test_scenario: str, duration_seconds: int = 60) -> Dict[str, Any]:
        """Run load testing for system capacity"""
        results = {
            'scenario': test_scenario,
            'duration_seconds': duration_seconds,
            'start_time': datetime.utcnow().isoformat(),
            'metrics_over_time': [],
            'peak_performance': {},
            'bottlenecks': []
        }
        
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            metrics = self.collect_system_metrics()
            results['metrics_over_time'].append(metrics.to_dict())
            time.sleep(1)  # Sample every second
        
        # Analyze results
        cpu_usage = [m['cpu_usage_percent'] for m in results['metrics_over_time']]
        memory_usage = [m['memory_usage_mb'] for m in results['metrics_over_time']]
        
        results['peak_performance'] = {
            'max_cpu_usage': max(cpu_usage),
            'max_memory_usage': max(memory_usage),
            'avg_cpu_usage': np.mean(cpu_usage),
            'avg_memory_usage': np.mean(memory_usage)
        }
        
        # Identify bottlenecks
        if max(cpu_usage) > 90:
            results['bottlenecks'].append('High CPU usage detected')
        if max(memory_usage) > psutil.virtual_memory().total * 0.9 / 1024 / 1024:
            results['bottlenecks'].append('High memory usage detected')
        
        return results


class ComparativeAnalyzer:
    """Compares different models and approaches"""
    
    def __init__(self):
        self.evaluation_results = []
    
    def add_evaluation_result(self, metrics: ModelEvaluationMetrics):
        """Add evaluation result for analysis"""
        self.evaluation_results.append(metrics)
    
    def generate_comparison_report(self) -> Dict[str, Any]:
        """Generate comprehensive comparison report"""
        if not self.evaluation_results:
            return {'error': 'No evaluation results available'}
        
        # Group by dataset
        dataset_groups = {}
        for result in self.evaluation_results:
            if result.dataset not in dataset_groups:
                dataset_groups[result.dataset] = []
            dataset_groups[result.dataset].append(result)
        
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'datasets': {},
            'overall_findings': {},
            'recommendations': []
        }
        
        for dataset, results in dataset_groups.items():
            dataset_report = self._analyze_dataset_results(results)
            report['datasets'][dataset] = dataset_report
        
        # Overall findings
        report['overall_findings'] = self._extract_overall_findings(report['datasets'])
        report['recommendations'] = self._generate_recommendations(report['overall_findings'])
        
        return report
    
    def _analyze_dataset_results(self, results: List[ModelEvaluationMetrics]) -> Dict[str, Any]:
        """Analyze results for a specific dataset"""
        analysis = {
            'model_count': len(results),
            'best_performing_model': None,
            'metric_comparisons': {},
            'performance_distribution': {}
        }
        
        if not results:
            return analysis
        
        # Find best performing model (based on F1 or accuracy)
        best_score = -1
        best_model = None
        
        for result in results:
            score = result.f1_score if result.f1_score is not None else result.accuracy or 0
            if score > best_score:
                best_score = score
                best_model = result.model_name
        
        analysis['best_performing_model'] = best_model
        
        # Metric comparisons
        metrics_to_compare = ['accuracy', 'precision', 'recall', 'f1_score', 'inference_time_ms']
        
        for metric in metrics_to_compare:
            values = []
            for result in results:
                value = getattr(result, metric)
                if value is not None:
                    values.append({'model': result.model_name, 'value': value})
            
            if values:
                analysis['metric_comparisons'][metric] = values
        
        return analysis
    
    def _extract_overall_findings(self, dataset_reports: Dict[str, Any]) -> Dict[str, Any]:
        """Extract overall findings across datasets"""
        findings = {
            'total_models_evaluated': sum(r['model_count'] for r in dataset_reports.values()),
            'best_models_by_dataset': {},
            'common_findings': [],
            'performance_trends': {}
        }
        
        # Best models
        for dataset, report in dataset_reports.items():
            findings['best_models_by_dataset'][dataset] = report['best_performing_model']
        
        # Common findings
        best_models = list(findings['best_models_by_dataset'].values())
        if len(set(best_models)) == 1:
            findings['common_findings'].append(f"All datasets show {best_models[0]} as best performer")
        else:
            st_gnn_count = best_models.count('ST-GNN')
            if st_gnn_count > len(best_models) / 2:
                findings['common_findings'].append("ST-GNN shows superior performance across datasets")
        
        return findings
    
    def _generate_recommendations(self, findings: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on findings"""
        recommendations = []
        
        best_models = findings.get('best_models_by_dataset', {})
        st_gnn_wins = sum(1 for model in best_models.values() if model == 'ST-GNN')
        
        if st_gnn_wins > len(best_models) / 2:
            recommendations.append("Adopt ST-GNN as primary model for spatio-temporal prediction tasks")
            recommendations.append("Consider ST-GNN for real-time anomaly detection")
        
        if findings.get('total_models_evaluated', 0) > 5:
            recommendations.append("Implement automated model evaluation pipeline")
            recommendations.append("Set up continuous model performance monitoring")
        
        return recommendations


class TimeSeriesEvaluator:
    """Evaluates time-series specific performance"""
    
    def __init__(self):
        self.temporal_splits = ['train', 'validation', 'test']
    
    def evaluate_temporal_stability(self, predictions: np.ndarray,
                                  actuals: np.ndarray, time_indices: np.ndarray) -> Dict[str, float]:
        """Evaluate how well model performs across different time periods"""
        stability_metrics = {}
        
        # Group by time periods (e.g., hour of day, day of week)
        unique_hours = np.unique(time_indices // 3600 % 24)  # Hours
        
        for hour in unique_hours:
            mask = (time_indices // 3600 % 24) == hour
            if np.sum(mask) > 10:  # Sufficient samples
                hour_preds = predictions[mask]
                hour_actuals = actuals[mask]
                
                mse = mean_squared_error(hour_actuals, hour_preds)
                stability_metrics[f'hour_{hour}_mse'] = mse
        
        # Overall temporal stability (coefficient of variation)
        hour_mses = list(stability_metrics.values())
        if hour_mses:
            stability_metrics['temporal_stability_cv'] = np.std(hour_mses) / np.mean(hour_mses)
        
        return stability_metrics
    
    def evaluate_spatial_generalization(self, predictions: np.ndarray,
                                      actuals: np.ndarray, locations: np.ndarray) -> Dict[str, float]:
        """Evaluate how well model generalizes across different locations"""
        generalization_metrics = {}
        
        # Group by location clusters (simplified - would use actual clustering)
        unique_locations = np.unique(locations, axis=0)
        
        for i, location in enumerate(unique_locations[:10]):  # Limit for performance
            distances = np.linalg.norm(locations - location, axis=1)
            nearby_mask = distances < 100  # Within 100 meters
            
            if np.sum(nearby_mask) > 10:
                location_preds = predictions[nearby_mask]
                location_actuals = actuals[nearby_mask]
                
                mse = mean_squared_error(location_actuals, location_preds)
                generalization_metrics[f'location_cluster_{i}_mse'] = mse
        
        return generalization_metrics
