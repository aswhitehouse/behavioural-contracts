import time
from behavioural_contracts.health_monitor import HealthMonitor

def test_initial_health():
    monitor = HealthMonitor()
    assert monitor.status == "healthy"
    assert monitor.strikes == 0

def test_add_strike():
    monitor = HealthMonitor()
    monitor.add_strike("test_reason")
    assert monitor.strikes == 1
    assert monitor.status == "healthy"  # Still healthy with one strike

def test_max_strikes():
    monitor = HealthMonitor()
    
    # Add strikes up to max_strikes
    for _ in range(3):
        monitor.add_strike("test_reason")
    
    assert monitor.strikes == 3
    assert monitor.status == "unhealthy"

def test_strike_window():
    monitor = HealthMonitor(strike_window_seconds=1)  # Use 1 second window for testing
    
    # Add a strike
    monitor.add_strike("test_reason")
    assert monitor.strikes == 1
    
    # Wait for strike window to expire
    time.sleep(1.1)  # Wait slightly longer than the window
    
    # Add another strike
    monitor.add_strike("test_reason")
    assert monitor.strikes == 1  # Should reset to 1 since window expired

def test_reset():
    monitor = HealthMonitor()
    
    # Add some strikes
    for _ in range(2):
        monitor.add_strike("test_reason")
    
    assert monitor.strikes == 2
    
    # Reset the monitor
    monitor.reset()
    assert monitor.strikes == 0
    assert monitor.status == "healthy" 