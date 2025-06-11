from behavioural_contracts.temperature import TemperatureController

def test_fixed_temperature():
    controller = TemperatureController("fixed", [0.2, 0.6])
    temp = controller.get_temperature()
    assert 0.2 <= temp <= 0.6

def test_adaptive_temperature():
    controller = TemperatureController("adaptive", [0.2, 0.6])
    
    # Initial temperature should be in range
    initial_temp = controller.get_temperature()
    assert 0.2 <= initial_temp <= 0.6
    
    # After successful response, temperature should decrease
    controller.adjust(True)
    new_temp = controller.get_temperature()
    assert new_temp <= initial_temp
    
    # After failed response, temperature should increase
    controller.adjust(False)
    increased_temp = controller.get_temperature()
    assert increased_temp >= new_temp

def test_temperature_bounds():
    controller = TemperatureController("adaptive", [0.2, 0.6])
    
    # Force temperature to minimum
    for _ in range(10):
        controller.adjust(True)
    assert controller.get_temperature() >= 0.2
    
    # Force temperature to maximum
    for _ in range(10):
        controller.adjust(False)
    assert controller.get_temperature() <= 0.6 