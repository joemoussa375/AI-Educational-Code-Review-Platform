import math

# VIOLATION: Function name should be snake_case
def CalculateAreaOfCircle(Radius):
    # VIOLATION: Variable name should be snake_case (unless it's a constant)
    PI = 3.14159
    # VIOLATION: Variable name should be snake_case
    Area = PI * Radius * Radius
    return Area

# VIOLATION: Function call matches the bad name
print(CalculateAreaOfCircle(10))
