/**
 * MakFleet Dashboard - Chart Functions
 * Handles Chart.js visualizations for analytics
 */

// Chart instances
let eventChart = null;
let riskChart = null;

/**
 * Initialize or update the event distribution chart
 * @param {Object} eventSummary - Event summary data
 */
function updateEventChart(eventSummary) {
    const ctx = document.getElementById('eventChart').getContext('2d');
    
    const data = {
        labels: ['Harsh Braking', 'Rapid Accel', 'Overspeed', 'Idling'],
        datasets: [{
            data: [
                eventSummary.HARSH_BRAKING || 0,
                eventSummary.RAPID_ACCELERATION || 0,
                eventSummary.OVERSPEED || 0,
                eventSummary.IDLING || 0
            ],
            backgroundColor: [
                '#ef4444',  // Harsh Braking - Red
                '#8b5cf6',  // Rapid Acceleration - Purple
                '#f59e0b',  // Overspeed - Orange
                '#6b7280'   // Idling - Gray
            ],
            borderWidth: 0
        }]
    };
    
    const config = {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12,
                        padding: 10,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((context.raw / total) * 100).toFixed(1) : 0;
                            return `${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    };
    
    if (eventChart) {
        eventChart.data = data;
        eventChart.update();
    } else {
        eventChart = new Chart(ctx, config);
    }
}

/**
 * Initialize or update the driver risk score chart
 * @param {Array} riskData - Array of driver risk scores
 */
function updateRiskChart(riskData) {
    const ctx = document.getElementById('riskChart').getContext('2d');
    
    // Sort by risk score and take top 5
    const topDrivers = riskData.slice(0, 5);
    
    const labels = topDrivers.map(d => d.plate_number || `Driver ${d.driver_id}`);
    const riskScores = topDrivers.map(d => d.total_score);
    
    // Color based on risk level
    const backgroundColors = riskScores.map(score => {
        if (score >= 20) return '#ef4444';  // High risk - Red
        if (score >= 10) return '#f59e0b';  // Medium risk - Orange
        return '#22c55e';                    // Low risk - Green
    });
    
    const data = {
        labels: labels,
        datasets: [{
            label: 'Risk Score',
            data: riskScores,
            backgroundColor: backgroundColors,
            borderRadius: 5,
            barThickness: 20
        }]
    };
    
    const config = {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            const driver = topDrivers[context.dataIndex];
                            return `\nHarsh Braking: ${driver.harsh_braking}\nOverspeed: ${driver.overspeed}\nRapid Accel: ${driver.rapid_acceleration}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 10
                        }
                    }
                },
                y: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                }
            }
        }
    };
    
    if (riskChart) {
        riskChart.data = data;
        riskChart.update();
    } else {
        riskChart = new Chart(ctx, config);
    }
}

/**
 * Create a speed distribution chart
 * @param {Array} telemetryData - Array of telemetry readings
 */
function createSpeedDistributionChart(telemetryData) {
    const speedRanges = {
        '0-20': 0,
        '20-40': 0,
        '40-60': 0,
        '60-80': 0,
        '80+': 0
    };
    
    telemetryData.forEach(t => {
        if (t.speed < 20) speedRanges['0-20']++;
        else if (t.speed < 40) speedRanges['20-40']++;
        else if (t.speed < 60) speedRanges['40-60']++;
        else if (t.speed < 80) speedRanges['60-80']++;
        else speedRanges['80+']++;
    });
    
    const ctx = document.getElementById('speedDistributionChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(speedRanges),
            datasets: [{
                label: 'Readings',
                data: Object.values(speedRanges),
                backgroundColor: '#1e3c72',
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Create a daily trips chart
 * @param {Array} dailyData - Array of daily trip data
 */
function createDailyTripsChart(dailyData) {
    const ctx = document.getElementById('dailyTripsChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: dailyData.map(d => `Day ${d.day}`),
            datasets: [{
                label: 'Active Vehicles',
                data: dailyData.map(d => d.active_vehicles),
                borderColor: '#1e3c72',
                backgroundColor: 'rgba(30, 60, 114, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Create a dangerous zones heatmap data
 * @param {Array} zones - Array of dangerous zone data
 */
function createDangerousZonesData(zones) {
    return zones.map(zone => ({
        lat: zone.latitude,
        lng: zone.longitude,
        count: zone.events,
        types: zone.types
    }));
}

/**
 * Destroy all chart instances
 */
function destroyAllCharts() {
    if (eventChart) {
        eventChart.destroy();
        eventChart = null;
    }
    if (riskChart) {
        riskChart.destroy();
        riskChart = null;
    }
}
