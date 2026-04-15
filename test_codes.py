"""
Test Codes for AI Code Mentor
Paste each test individually into the frontend to evaluate review quality.
"""

# ============================================
# TEST 1: Logic Bug — List mutation during iteration
# Expected: 🔴 Critical issue detected
# ============================================
def ProcessData(InputList):
    import os
    for item in InputList:
        if item % 2 == 0:
            InputList.remove(item)
    return InputList


# ============================================
# TEST 2: Security Issue — eval() and unclosed file
# Expected: 🔴 Critical (eval is dangerous, file not closed)
# ============================================
def calculate(user_input):
    result = eval(user_input)
    return result

def ReadFile(path):
    f = open(path, "r")
    data = f.read()
    return data


# ============================================
# TEST 3: Inefficient Algorithm — O(n²) nested loops
# Expected: 🟡 Warning (use sets for O(n) lookup)
# ============================================
def find_duplicates(list1, list2):
    duplicates = []
    for item in list1:
        for other in list2:
            if item == other:
                if item not in duplicates:
                    duplicates.append(item)
    return duplicates


# ============================================
# TEST 4: Bad Error Handling — bare except, unclosed file
# Expected: 🔴 Critical (bare except), 🟡 Style (naming)
# ============================================
import json

def ParseConfig(FilePath):
    try:
        file = open(FilePath)
        Data = json.load(file)
        return Data
    except:
        pass


# ============================================
# TEST 5: Clean Code — should get NO critical issues
# Expected: 🟢 Good code, minimal or no issues
# ============================================
def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


# ============================================
# TEST 6: PEP-8 Style Violations
# Expected: 🟡 Style (flag CamelCase, bad spacing)
# ============================================
def ProcessUserData  ( UserID , database_connection):
  UserData=database_connection.get(UserID)
  if UserData!=None:
    return UserData


# ============================================
# TEST 7: Security — Hardcoded Secrets
# Expected: 🔴 Critical (hardcoded API key)
# ============================================
def connect_to_payment_gateway():
    api_key = "sk_live_1234567890abcdef1234567890"
    url = f"https://api.stripe.com/v1/charges?key={api_key}"
    return url


# ============================================
# TEST 8: Logic Bug — Off-by-one error
# Expected: 🔴 Critical (IndexError out of bounds risk)
# ============================================
def get_last_element(items):
    index = len(items)
    return items[index]


# ============================================
# TEST 9: Resource Leak — Unclosed File
# Expected: 🔴 Critical (Use `with open() as...`)
# ============================================
def write_log(message):
    file = open("application.log", "a")
    file.write(message + "\\n")
   
    # Missing file.close()


# ============================================
# TEST 10: Advanced Clean Code — Map/Lambda
# Expected: 🟢 Good code, no hallucinations
# ============================================
def extract_active_users(users):
    """Returns a list of emails for active users."""
    return list(map(lambda u: u['email'], filter(lambda u: u.get('is_active'), users)))


# ============================================
# TEST 11: Stress Test — Monolithic Function
# Expected: 🟡 Style / Warning (Cyclomatic complexity, suggest modularization)
# ============================================
def handle_user_request(request_data, db, email_service, logger):
    if not request_data:
        logger.error("Empty request")
        return {"status": "error"}
    
    user_id = request_data.get("user_id")
    if user_id:
        user = db.get_user(user_id)
        if user:
            if user.is_active:
                action = request_data.get("action")
                if action == "update_profile":
                    db.update(user_id, request_data.get("data"))
                    logger.info("Profile updated")
                    email_service.send(user.email, "Profile Updated")
                    return {"status": "success"}
                elif action == "delete_account":
                    db.delete(user_id)
                    logger.info("Account deleted")
                    email_service.send(user.email, "Goodbye")
                    return {"status": "success"}
                else:
                    logger.error("Unknown action")
                    return {"status": "invalid_action"}
            else:
                logger.warning("Inactive user tried to act")
                return {"status": "inactive"}
        else:
            logger.error("User not found")
            return {"status": "not_found"}
    else:
        logger.error("Missing user_id")
        return {"status": "missing_id"}
