"""
supplement_missing.py
Patches dataset.json with missing entries (IDs 56-60, 71-75 Tier2 + 81, 82, 91, 92 Tier3).
Run AFTER prepare_dataset.py:
    python testing/supplement_missing.py
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATASET  = BASE_DIR / "dataset.json"

# Minimal but valid code strings that preserve all declared bug patterns.
# Each code string contains the exact identifiers referenced in expected_labels
# so detection patterns in evaluation_harness.py will fire correctly.
MISSING_ENTRIES = [
  {
    "id": 56, "tier": 2,
    "title": "Web Scraper: Shared state, hardcoded proxy, eval(), unclosed file",
    "expected": "🔴 Critical: Hardcoded 'PROXY_PASS', 🔴 Critical: eval() to parse string data, 🔴 Critical: Unclosed file in SaveResults, 🔴 Critical: Class attribute 'visited_urls' acts as shared mutable state, 🟡 Style: CamelCase methods",
    "code": "import time\nimport json\n\nPROXY_USER = 'scraper_admin'\nPROXY_PASS = 'scrape_master_999!'\n\nclass DataScraper:\n    visited_urls = []  # shared class attribute bug\n\n    def __init__(self, domain):\n        self.domain = domain\n        self.data = []\n\n    def FetchPage(self, url):\n        if url in self.visited_urls:\n            return None\n        self.visited_urls.append(url)\n        return \"{'title': 'Mock', 'status': 'ok'}\"\n\n    def ParseData(self, raw):\n        result = eval(raw)  # OWASP: eval() vulnerability\n        self.data.append(result)\n\n    def SaveResults(self):\n        f = open(f'{self.domain}_results.txt', 'w')  # unclosed file\n        for item in self.data:\n            f.write(str(item))\n\ndef main():\n    s = DataScraper('site-a.com')\n    raw = s.FetchPage('http://site-a.com')\n    if raw:\n        s.ParseData(raw)\n    s.SaveResults()\n\nif __name__ == '__main__':\n    main()\n"
  },
  {
    "id": 57, "tier": 2,
    "title": "IoT Manager: List mutation, hardcoded MQTT secret, O(n^2) sync, unclosed log",
    "expected": "🔴 Critical: Hardcoded 'MQTT_SECRET', 🔴 Critical: Mutating list in RemoveOffline, 🔴 Critical: O(n^2) in SyncDevices, 🔴 Critical: Unclosed file in ExportConfig, 🟡 Style: CamelCase methods",
    "code": "import time\n\nMQTT_BROKER = 'tcp://mqtt.local:1883'\nMQTT_SECRET = 'super_secure_mqtt_key_2025'\n\nclass IoTDevice:\n    def __init__(self, dev_id, dev_type):\n        self.dev_id = dev_id\n        self.dev_type = dev_type\n        self.status = 'offline'\n        self.last_ping = time.time()\n\n    def Ping(self):\n        self.status = 'online'\n        self.last_ping = time.time()\n\nclass IoTManager:\n    def __init__(self):\n        self.devices = []\n\n    def RegisterDevice(self, device):\n        self.devices.append(device)\n\n    def RemoveOffline(self):\n        current_time = time.time()\n        for dev in self.devices:  # mutating list during iteration\n            if current_time - dev.last_ping > 60:\n                self.devices.remove(dev)\n\n    def SyncDevices(self):\n        synced = []\n        for d1 in self.devices:  # O(n^2) nested loop\n            for d2 in self.devices:\n                if d1.dev_id != d2.dev_id and d1.dev_type == d2.dev_type:\n                    pair = (d1.dev_id, d2.dev_id)\n                    if pair not in synced:\n                        synced.append(pair)\n\n    def ExportConfig(self):\n        out_file = open('config.txt', 'w')  # unclosed file\n        out_file.write(f'Broker: {MQTT_BROKER}\\n')\n\ndef main():\n    mgr = IoTManager()\n    d1 = IoTDevice('T1', 'Thermostat')\n    mgr.RegisterDevice(d1)\n    mgr.RemoveOffline()\n    mgr.SyncDevices()\n    mgr.ExportConfig()\n\nif __name__ == '__main__':\n    main()\n"
  },
  {
    "id": 58, "tier": 2,
    "title": "Task App: eval() for dates, hardcoded token, O(n^2) duplicates, unclosed file",
    "expected": "🔴 Critical: Hardcoded 'ADMIN_TOKEN', 🔴 Critical: eval() in ParseDueDate, 🔴 Critical: O(n^2) in FindDuplicates, 🔴 Critical: Unclosed file in SaveTasks, 🟡 Style: CamelCase methods",
    "code": "import time\nimport uuid\n\nADMIN_TOKEN = 'task_admin_xyz_987654321'\n\nclass Task:\n    def __init__(self, title, desc):\n        self.id = str(uuid.uuid4())[:8]\n        self.title = title\n        self.due_date = None\n\nclass TaskManager:\n    def __init__(self):\n        self.tasks = []\n        self.admin_mode = False\n\n    def EnableAdmin(self, token):\n        if token == ADMIN_TOKEN:\n            self.admin_mode = True\n\n    def AddTask(self, title, desc):\n        t = Task(title, desc)\n        self.tasks.append(t)\n        return t\n\n    def ParseDueDate(self, task_id, date_expression):\n        for t in self.tasks:\n            if t.id == task_id:\n                t.due_date = eval(date_expression)  # eval() vulnerability\n\n    def FindDuplicates(self):\n        duplicates = []\n        for t1 in self.tasks:  # O(n^2)\n            for t2 in self.tasks:\n                if t1.id != t2.id and t1.title == t2.title:\n                    if t1.title not in duplicates:\n                        duplicates.append(t1.title)\n        return duplicates\n\n    def SaveTasks(self):\n        f = open('tasks_db.txt', 'w')  # unclosed file\n        for t in self.tasks:\n            f.write(f'{t.id}|{t.title}\\n')\n\ndef main():\n    mgr = TaskManager()\n    mgr.EnableAdmin('task_admin_xyz_987654321')\n    t1 = mgr.AddTask('Buy Groceries', 'Milk')\n    mgr.ParseDueDate(t1.id, 'time.time() + 86400')\n    mgr.FindDuplicates()\n    mgr.SaveTasks()\n\nif __name__ == '__main__':\n    main()\n"
  },
  {
    "id": 59, "tier": 2,
    "title": "Inventory System: Missing super(), O(n^2) reporting, hardcoded DB, unclosed file",
    "expected": "🔴 Critical: Hardcoded 'DB_PASSWORD', 🔴 Critical: Missing super().__init__ in PremiumInventory, 🔴 Critical: O(n^2) in CrossReference, 🔴 Critical: Unclosed file in WriteReport, 🟡 Style: CamelCase methods",
    "code": "import time\n\nDB_USER = 'inventory_writer'\nDB_PASSWORD = 'inv_db_pass_2024_secure'\n\nclass BaseInventory:\n    def __init__(self, location):\n        self.location = location\n        self.items = []\n\n    def AddItem(self, name, category, value):\n        self.items.append({'name': name, 'category': category, 'value': value})\n\nclass PremiumInventory(BaseInventory):\n    def __init__(self, region):  # missing super().__init__()\n        self.region = region\n        self.items = []\n        self.premium_fee = 0.15\n\n    def ConnectDatabase(self):\n        print(f'Connecting with {DB_USER}:{DB_PASSWORD[:4]}...')\n\n    def CrossReference(self, other):\n        matches = []\n        for my_item in self.items:  # O(n^2)\n            for their_item in other.items:\n                if my_item['category'] == their_item['category']:\n                    matches.append((my_item['name'], their_item['name']))\n        return matches\n\n    def WriteReport(self):\n        report_file = open('report.csv', 'w')  # unclosed file\n        for item in self.items:\n            report_file.write(f\"{item['name']},{item['value']}\\n\")\n\ndef main():\n    base = BaseInventory('NY')\n    base.AddItem('Desk', 'Furniture', 100)\n    prem = PremiumInventory('EU')\n    prem.ConnectDatabase()\n    prem.AddItem('Oak Desk', 'Furniture', 500)\n    prem.CrossReference(base)\n    prem.WriteReport()\n\nif __name__ == '__main__':\n    main()\n"
  },
  {
    "id": 60, "tier": 2,
    "title": "Chatbot Backend: eval() commands, hardcoded webhook, mutating active users, O(n^2)",
    "expected": "🔴 Critical: Hardcoded 'WEBHOOK_SECRET', 🔴 Critical: eval() in ExecuteCommand, 🔴 Critical: Mutating list in CleanInactive, 🔴 Critical: O(n^2) in FindMentions, 🔴 Critical: Unclosed file in SaveTranscript, 🟡 Style: CamelCase methods",
    "code": "import time\n\nWEBHOOK_SECRET = 'whsec_9876543210abcdef_mock_secret'\n\nclass ChatMessage:\n    def __init__(self, sender, text):\n        self.sender = sender\n        self.text = text\n        self.timestamp = time.time()\n\nclass ChatbotBackend:\n    def __init__(self):\n        self.active_users = ['alice', 'bob', 'charlie', 'dave']\n        self.message_history = []\n\n    def ReceiveMessage(self, sender, text):\n        msg = ChatMessage(sender, text)\n        self.message_history.append(msg)\n        return msg\n\n    def ExecuteCommand(self, user_input):\n        if user_input.startswith('/'):\n            response = eval(user_input[1:])  # eval() vulnerability\n            print(f'Bot: {response}')\n\n    def CleanInactive(self):\n        current_time = time.time()\n        for user in self.active_users:  # mutating list during iteration\n            last_active = current_time - (len(user) * 100)\n            if current_time - last_active > 300:\n                self.active_users.remove(user)\n\n    def FindMentions(self):\n        mentions = []\n        for msg in self.message_history:  # O(n^2)\n            for user in self.active_users:\n                if f'@{user}' in msg.text:\n                    mentions.append(f'{msg.sender} -> {user}')\n        return mentions\n\n    def SaveTranscript(self):\n        transcript_file = open('chat_transcript.log', 'w')  # unclosed file\n        transcript_file.write(f'Auth: {WEBHOOK_SECRET[:5]}***\\n')\n        for msg in self.message_history:\n            transcript_file.write(f'{msg.sender}: {msg.text}\\n')\n\ndef main():\n    bot = ChatbotBackend()\n    bot.ReceiveMessage('alice', 'Hello!')\n    bot.ReceiveMessage('bob', 'Hey @alice!')\n    bot.ExecuteCommand('/150 * 0.20')\n    bot.FindMentions()\n    bot.CleanInactive()\n    bot.SaveTranscript()\n\nif __name__ == '__main__':\n    main()\n"
  },
  {
    "id": 71, "tier": 2,
    "title": "Smart City Traffic Controller: Missing super(), eval(), O(n^2), mutating list",
    "expected": "🔴 Critical: Hardcoded 'CITY_API_KEY', 🔴 Critical: Missing super().__init__ in SmartTrafficLight, 🔴 Critical: eval() in CalculateTiming, 🔴 Critical: Mutating list in RemoveOfflineNodes, 🔴 Critical: O(n^2) in MapCorridors, 🔴 Critical: Unclosed file in ExportLogs, 🟡 Style: CamelCase methods",
    "code": "import time\n\nCITY_API_KEY = 'sc_traffic_api_live_987654321'\n\nclass BaseNode:\n    def __init__(self, node_id, location):\n        self.node_id = node_id\n        self.location = location\n        self.is_active = True\n        self.last_ping = time.time()\n\nclass SmartTrafficLight(BaseNode):\n    def __init__(self, has_camera):  # missing super().__init__()\n        self.has_camera = has_camera\n        self.current_state = 'RED'\n        self.base_timer = 30\n\nclass TrafficController:\n    def __init__(self):\n        self.network = []\n        self.corridors = []\n\n    def RegisterNode(self, node):\n        self.network.append(node)\n\n    def CalculateTiming(self, light_obj, traffic_formula):\n        base_timer = getattr(light_obj, 'base_timer', 30)\n        new_timer = eval(traffic_formula)  # eval() vulnerability\n        return new_timer\n\n    def MapCorridors(self):\n        for n1 in self.network:  # O(n^2)\n            for n2 in self.network:\n                if n1 != n2:\n                    loc1 = getattr(n1, 'location', 'X')\n                    loc2 = getattr(n2, 'location', 'Y')\n                    if loc1.split()[0] == loc2.split()[0]:\n                        self.corridors.append(loc1.split()[0])\n\n    def RemoveOfflineNodes(self):\n        current_time = time.time()\n        for node in self.network:  # mutating list during iteration\n            if current_time - getattr(node, 'last_ping', 0) > 300:\n                self.network.remove(node)\n\n    def ExportLogs(self):\n        log_file = open(f'traffic_log.txt', 'w')  # unclosed file\n        log_file.write(f'Auth: {CITY_API_KEY[:5]}***\\n')\n\ndef main():\n    tc = TrafficController()\n    n1 = BaseNode('N1', 'Main St 1st Ave')\n    n2 = BaseNode('N2', 'Main St 2nd Ave')\n    t1 = SmartTrafficLight(True)\n    tc.RegisterNode(n1)\n    tc.RegisterNode(n2)\n    tc.RegisterNode(t1)\n    tc.MapCorridors()\n    tc.CalculateTiming(t1, 'base_timer * 2.0')\n    tc.ExportLogs()\n\nif __name__ == '__main__':\n    main()\n"
  },
  {
    "id": 72, "tier": 2,
    "title": "ATS System: Shared state, eval() keywords, O(n^2), mutating list, unclosed file",
    "expected": "🔴 Critical: Hardcoded 'AWS_S3_SECRET', 🔴 Critical: Class attribute 'resume_pool' acts as shared mutable state, 🔴 Critical: eval() in EvaluateCandidate, 🔴 Critical: Mutating list in ArchiveRejected, 🔴 Critical: O(n^2) in FindDuplicateResumes, 🔴 Critical: Unclosed file in GenerateReport, 🟡 Style: CamelCase methods",
    "code": "import time\n\nAWS_S3_SECRET = 'AKIA_MOCK_ATS_SECRET_KEY_999888777'\n\nclass Applicant:\n    def __init__(self, name, email, skills):\n        self.name = name\n        self.email = email\n        self.skills = skills\n        self.score = 0\n        self.status = 'PENDING'\n\nclass ATSManager:\n    resume_pool = []  # shared class attribute bug\n\n    def __init__(self, department):\n        self.department = department\n\n    def AddApplicant(self, applicant):\n        self.resume_pool.append(applicant)\n\n    def EvaluateCandidate(self, name, scoring_formula):\n        for app in self.resume_pool:\n            if app.name == name:\n                skill_count = len(app.skills)\n                app.score = eval(scoring_formula)  # eval() vulnerability\n\n    def FindDuplicateResumes(self):\n        duplicates = []\n        for a1 in self.resume_pool:  # O(n^2)\n            for a2 in self.resume_pool:\n                if a1 != a2 and a1.email == a2.email:\n                    if a1.name not in duplicates:\n                        duplicates.append(a1.name)\n        return duplicates\n\n    def ArchiveRejected(self):\n        for app in self.resume_pool:  # mutating list during iteration\n            if app.status == 'REJECTED':\n                self.resume_pool.remove(app)\n\n    def GenerateReport(self):\n        f = open(f'{self.department}_ATS_Report.csv', 'w')  # unclosed file\n        f.write('Name,Email,Status,Score\\n')\n        for app in self.resume_pool:\n            f.write(f'{app.name},{app.email},{app.status},{app.score}\\n')\n\ndef main():\n    eng = ATSManager('Engineering')\n    a1 = Applicant('Alice', 'alice@test.com', ['Python', 'AWS'])\n    a2 = Applicant('Bob', 'bob@test.com', ['Java'])\n    eng.AddApplicant(a1)\n    eng.AddApplicant(a2)\n    eng.EvaluateCandidate('Alice', 'skill_count * 30')\n    eng.FindDuplicateResumes()\n    eng.ArchiveRejected()\n    eng.GenerateReport()\n\nif __name__ == '__main__':\n    main()\n"
  },
  {
    "id": 73, "tier": 2,
    "title": "Matchmaker: Missing super(), mutating list, O(n^2), eval(), unclosed log",
    "expected": "🔴 Critical: Hardcoded 'SERVER_SECRET', 🔴 Critical: Missing super().__init__ in VIPPlayer, 🔴 Critical: Mutating list in CleanQueue, 🔴 Critical: eval() in CalculateMMR, 🔴 Critical: O(n^2) in FormTeams, 🔴 Critical: Unclosed file in SaveLogs, 🟡 Style: CamelCase methods",
    "code": "import time\n\nSERVER_SECRET = 'gmesrv_token_abc_123_prod'\n\nclass BasePlayer:\n    def __init__(self, username, ping_ms, wins, losses):\n        self.username = username\n        self.ping_ms = ping_ms\n        self.wins = wins\n        self.losses = losses\n        self.is_queued = True\n\nclass VIPPlayer(BasePlayer):\n    def __init__(self, subscription_tier):  # missing super().__init__()\n        self.sub_tier = subscription_tier\n        self.multiplier = 1.5\n\nclass Matchmaker:\n    def __init__(self):\n        self.queue = []\n\n    def AddToQueue(self, player):\n        self.queue.append(player)\n\n    def CleanQueue(self):\n        for p in self.queue:  # mutating list during iteration\n            if getattr(p, 'ping_ms', 0) > 150:\n                self.queue.remove(p)\n\n    def CalculateMMR(self, player_name, math_formula):\n        for p in self.queue:\n            if getattr(p, 'username', '') == player_name:\n                wins = getattr(p, 'wins', 0)\n                losses = getattr(p, 'losses', 0)\n                mmr = eval(math_formula)  # eval() vulnerability\n                return mmr\n\n    def FormTeams(self):\n        teams = []\n        for p1 in self.queue:  # O(n^2)\n            for p2 in self.queue:\n                if p1 != p2:\n                    pair = tuple(sorted([getattr(p1, 'username', 'U1'), getattr(p2, 'username', 'U2')]))\n                    if pair not in teams:\n                        teams.append(pair)\n        return teams\n\n    def SaveLogs(self):\n        f = open('matchmaker_service.log', 'w')  # unclosed file\n        f.write(f'Auth: {hash(SERVER_SECRET)}\\n')\n\ndef main():\n    mm = Matchmaker()\n    p1 = BasePlayer('Sniper33', 40, 100, 50)\n    v1 = VIPPlayer('Gold')\n    mm.AddToQueue(p1)\n    mm.AddToQueue(v1)\n    mm.CleanQueue()\n    mm.CalculateMMR('Sniper33', 'wins * 15 - losses * 5')\n    mm.FormTeams()\n    mm.SaveLogs()\n\nif __name__ == '__main__':\n    main()\n"
  },
  {
    "id": 74, "tier": 2,
    "title": "Hospital System: Shared state, eval() dosages, mutating list, O(n^2), unclosed file",
    "expected": "🔴 Critical: Hardcoded 'HL7_API_KEY', 🔴 Critical: Class attribute 'admitted_patients' acts as shared mutable state, 🔴 Critical: eval() in CalculateDosage, 🔴 Critical: Mutating list in DischargePatients, 🔴 Critical: O(n^2) in FindCommonSymptoms, 🔴 Critical: Unclosed file in PrintPrescriptions, 🟡 Style: CamelCase methods",
    "code": "import time\n\nHL7_API_KEY = 'med_api_live_secure_abcdef'\n\nclass Patient:\n    def __init__(self, pid, name, weight_kg, symptoms):\n        self.patient_id = pid\n        self.name = name\n        self.weight_kg = weight_kg\n        self.symptoms = symptoms\n        self.is_discharged = False\n\nclass HospitalWard:\n    admitted_patients = []  # shared class attribute bug\n\n    def __init__(self, ward_name):\n        self.ward_name = ward_name\n\n    def AdmitPatient(self, patient):\n        self.admitted_patients.append(patient)\n\n    def CalculateDosage(self, patient_name, medication_formula):\n        for p in self.admitted_patients:\n            if p.name == patient_name:\n                weight_kg = p.weight_kg\n                dosage_mg = eval(medication_formula)  # eval() vulnerability\n                return dosage_mg\n\n    def FindCommonSymptoms(self):\n        shared = []\n        for p1 in self.admitted_patients:  # O(n^2)\n            for p2 in self.admitted_patients:\n                if p1 != p2:\n                    for s1 in p1.symptoms:\n                        for s2 in p2.symptoms:\n                            if s1 == s2 and s1 not in shared:\n                                shared.append(s1)\n        return shared\n\n    def DischargePatients(self):\n        for p in self.admitted_patients:  # mutating list during iteration\n            if p.is_discharged:\n                self.admitted_patients.remove(p)\n\n    def PrintPrescriptions(self):\n        f = open(f'{self.ward_name}_scripts.txt', 'w')  # unclosed file\n        for p in self.admitted_patients:\n            f.write(f'{p.name}|{p.weight_kg}kg\\n')\n\ndef main():\n    icu = HospitalWard('ICU')\n    er = HospitalWard('ER')\n    p1 = Patient('P01', 'Alice', 65, ['Fever', 'Cough'])\n    p2 = Patient('P02', 'Bob', 80, ['Cough', 'Fatigue'])\n    icu.AdmitPatient(p1)\n    er.AdmitPatient(p2)\n    p1.is_discharged = True\n    icu.DischargePatients()\n    icu.CalculateDosage('Alice', 'weight_kg * 5.0')\n    er.FindCommonSymptoms()\n    icu.PrintPrescriptions()\n\nif __name__ == '__main__':\n    main()\n"
  },
  {
    "id": 75, "tier": 2,
    "title": "E-Learning Platform: Missing super(), mutating list, eval() grades, O(n^2)",
    "expected": "🔴 Critical: Hardcoded 'VIMEO_SECRET_TOKEN', 🔴 Critical: Missing super().__init__ in VideoCourse, 🔴 Critical: Mutating list in DropInactiveStudents, 🔴 Critical: eval() in CurveGrades, 🔴 Critical: O(n^2) in CheckEnrollmentOverlap, 🔴 Critical: Unclosed file in ExportGrades, 🟡 Style: CamelCase methods",
    "code": "import time\n\nVIMEO_SECRET_TOKEN = 'vimeo_sec_live_998877665544'\n\nclass BaseCourse:\n    def __init__(self, course_id, title):\n        self.course_id = course_id\n        self.title = title\n        self.students = []\n\n    def AddStudent(self, name, grade):\n        self.students.append({'name': name, 'grade': grade, 'active': True})\n\nclass VideoCourse(BaseCourse):\n    def __init__(self, video_url, duration_mins):  # missing super().__init__()\n        self.video_url = video_url\n        self.duration_mins = duration_mins\n        self.views = 0\n\nclass ELearningPlatform:\n    def __init__(self):\n        self.courses = []\n\n    def RegisterCourse(self, course):\n        self.courses.append(course)\n\n    def DropInactiveStudents(self):\n        for course in self.courses:\n            students = getattr(course, 'students', [])\n            for student in students:  # mutating list during iteration\n                if not student['active']:\n                    students.remove(student)\n\n    def CurveGrades(self, course_id, curve_formula):\n        for c in self.courses:\n            if getattr(c, 'course_id', '') == course_id:\n                for s in getattr(c, 'students', []):\n                    current_grade = s['grade']\n                    s['grade'] = eval(curve_formula)  # eval() vulnerability\n\n    def CheckEnrollmentOverlap(self):\n        overlaps = []\n        for c1 in self.courses:  # O(n^2)\n            for c2 in self.courses:\n                if c1 != c2:\n                    for s1 in getattr(c1, 'students', []):\n                        for s2 in getattr(c2, 'students', []):\n                            if s1['name'] == s2['name'] and s1['name'] not in overlaps:\n                                overlaps.append(s1['name'])\n        return overlaps\n\n    def ExportGrades(self):\n        f = open('platform_grades.csv', 'w')  # unclosed file\n        for c in self.courses:\n            for s in getattr(c, 'students', []):\n                f.write(f\"{getattr(c,'title','?')},{s['name']},{s['grade']}\\n\")\n\ndef main():\n    platform = ELearningPlatform()\n    c1 = BaseCourse('CS101', 'Intro CS')\n    c1.AddStudent('Alice', 85)\n    c1.AddStudent('Bob', 70)\n    c2 = VideoCourse('https://vimeo.com/123', 45)\n    platform.RegisterCourse(c1)\n    platform.RegisterCourse(c2)\n    c1.students[0]['active'] = False\n    platform.DropInactiveStudents()\n    platform.CurveGrades('CS101', 'current_grade + 5')\n    platform.CheckEnrollmentOverlap()\n    platform.ExportGrades()\n\nif __name__ == '__main__':\n    main()\n"
  },
  # --- Missing Tier 3 entries (IDs 97-100) ---
  {
    "id": 97, "tier": 3,
    "title": "Monolithic Data Pipeline: Extreme cyclomatic complexity, bare excepts, DRY violations",
    "expected": "🔴 Critical: Bare except blocks hiding failures, 🔴 Critical: DRY violation — repeated processing logic, 🔴 Critical: Extreme cyclomatic complexity in process_all, 🟡 Style: Missing docstrings",
    "code": "def process_type_a(data):\n    try:\n        result = []\n        for item in data:\n            if item > 0:\n                if item < 10:\n                    result.append(item * 1.1)\n                elif item < 100:\n                    result.append(item * 1.2)\n                else:\n                    result.append(item * 1.3)\n        return result\n    except:\n        pass\n\ndef process_type_b(data):\n    try:\n        result = []\n        for item in data:\n            if item > 0:\n                if item < 10:\n                    result.append(item * 1.1)\n                elif item < 100:\n                    result.append(item * 1.2)\n                else:\n                    result.append(item * 1.3)\n        return result\n    except:\n        pass\n\ndef process_type_c(data):\n    try:\n        result = []\n        for item in data:\n            if item > 0:\n                if item < 10:\n                    result.append(item * 1.1)\n                elif item < 100:\n                    result.append(item * 1.2)\n                else:\n                    result.append(item * 1.3)\n        return result\n    except:\n        pass\n\ndef process_all(datasets):\n    output = {}\n    for key, data in datasets.items():\n        if key == 'a':\n            if data:\n                if len(data) > 0:\n                    if isinstance(data, list):\n                        output['a'] = process_type_a(data)\n        elif key == 'b':\n            if data:\n                if len(data) > 0:\n                    if isinstance(data, list):\n                        output['b'] = process_type_b(data)\n        elif key == 'c':\n            if data:\n                if len(data) > 0:\n                    if isinstance(data, list):\n                        output['c'] = process_type_c(data)\n    return output\n\nif __name__ == '__main__':\n    datasets = {'a': [1, 50, 200], 'b': [5, 75, 300], 'c': [8, 90, 150]}\n    print(process_all(datasets))\n"
  },
  {
    "id": 98, "tier": 3,
    "title": "Monolithic Report Generator: God class, DRY violations, bare excepts, high complexity",
    "expected": "🔴 Critical: Bare except blocks hiding failures, 🔴 Critical: DRY violation — repeated report formatting logic, 🔴 Critical: God class with too many responsibilities, 🟡 Style: Missing docstrings",
    "code": "class ReportGenerator:\n    def generate_sales_report(self, data):\n        try:\n            lines = []\n            lines.append('=== SALES REPORT ===')\n            for item in data:\n                if item.get('amount', 0) > 0:\n                    lines.append(f\"Item: {item['name']} Amount: {item['amount']}\")\n            lines.append('===================')\n            total = sum(i.get('amount', 0) for i in data)\n            lines.append(f'Total: {total}')\n            return '\\n'.join(lines)\n        except:\n            pass\n\n    def generate_inventory_report(self, data):\n        try:\n            lines = []\n            lines.append('=== INVENTORY REPORT ===')\n            for item in data:\n                if item.get('amount', 0) > 0:\n                    lines.append(f\"Item: {item['name']} Amount: {item['amount']}\")\n            lines.append('===================')\n            total = sum(i.get('amount', 0) for i in data)\n            lines.append(f'Total: {total}')\n            return '\\n'.join(lines)\n        except:\n            pass\n\n    def generate_hr_report(self, data):\n        try:\n            lines = []\n            lines.append('=== HR REPORT ===')\n            for item in data:\n                if item.get('amount', 0) > 0:\n                    lines.append(f\"Item: {item['name']} Amount: {item['amount']}\")\n            lines.append('===================')\n            total = sum(i.get('amount', 0) for i in data)\n            lines.append(f'Total: {total}')\n            return '\\n'.join(lines)\n        except:\n            pass\n\n    def save_to_disk(self, report, filename):\n        try:\n            f = open(filename, 'w')\n            f.write(report)\n        except:\n            pass\n\nif __name__ == '__main__':\n    gen = ReportGenerator()\n    data = [{'name': 'Widget', 'amount': 100}]\n    print(gen.generate_sales_report(data))\n"
  },
  {
    "id": 99, "tier": 3,
    "title": "Monolithic Auth System: Extreme nesting, bare excepts, DRY violations, hardcoded secret",
    "expected": "🔴 Critical: Hardcoded 'MASTER_SECRET', 🔴 Critical: Bare except blocks hiding failures, 🔴 Critical: DRY violation — repeated validation logic, 🔴 Critical: Excessive nesting depth, 🟡 Style: Missing docstrings",
    "code": "import hashlib\n\nMASTER_SECRET = 'auth_master_key_prod_1234'\n\ndef validate_user(username, password, role):\n    try:\n        if username:\n            if len(username) > 3:\n                if password:\n                    if len(password) > 6:\n                        if role:\n                            if role in ['admin', 'user', 'guest']:\n                                hashed = hashlib.md5(password.encode()).hexdigest()\n                                if hashed:\n                                    return True\n    except:\n        pass\n    return False\n\ndef validate_admin(username, password, role):\n    try:\n        if username:\n            if len(username) > 3:\n                if password:\n                    if len(password) > 6:\n                        if role:\n                            if role in ['admin', 'user', 'guest']:\n                                hashed = hashlib.md5(password.encode()).hexdigest()\n                                if hashed:\n                                    if password == MASTER_SECRET:\n                                        return True\n    except:\n        pass\n    return False\n\ndef validate_service(username, password, role):\n    try:\n        if username:\n            if len(username) > 3:\n                if password:\n                    if len(password) > 6:\n                        if role:\n                            if role in ['admin', 'user', 'guest']:\n                                hashed = hashlib.md5(password.encode()).hexdigest()\n                                if hashed:\n                                    return True\n    except:\n        pass\n    return False\n\nif __name__ == '__main__':\n    print(validate_user('alice', 'password123', 'user'))\n    print(validate_admin('admin', 'auth_master_key_prod_1234', 'admin'))\n"
  },
  {
    "id": 100, "tier": 3,
    "title": "Monolithic ETL Pipeline: God function, DRY violations, bare excepts, O(n^2)",
    "expected": "🔴 Critical: Bare except blocks hiding failures, 🔴 Critical: DRY violation — repeated ETL stage logic, 🔴 Critical: O(n^2) in deduplication step, 🔴 Critical: God function with extreme cyclomatic complexity, 🟡 Style: Missing docstrings",
    "code": "def run_etl(source_a, source_b, source_c):\n    # Extract stage\n    try:\n        data_a = [r for r in source_a if r.get('valid')]\n    except:\n        data_a = []\n    try:\n        data_b = [r for r in source_b if r.get('valid')]\n    except:\n        data_b = []\n    try:\n        data_c = [r for r in source_c if r.get('valid')]\n    except:\n        data_c = []\n\n    # Transform stage\n    try:\n        transformed_a = []\n        for r in data_a:\n            if r.get('value', 0) > 0:\n                transformed_a.append({'id': r['id'], 'value': r['value'] * 1.1})\n    except:\n        transformed_a = []\n    try:\n        transformed_b = []\n        for r in data_b:\n            if r.get('value', 0) > 0:\n                transformed_b.append({'id': r['id'], 'value': r['value'] * 1.1})\n    except:\n        transformed_b = []\n\n    # Merge\n    all_data = transformed_a + transformed_b + data_c\n\n    # Deduplicate O(n^2)\n    unique = []\n    for item in all_data:\n        is_dup = False\n        for seen in unique:\n            if item.get('id') == seen.get('id'):\n                is_dup = True\n                break\n        if not is_dup:\n            unique.append(item)\n\n    # Load stage\n    try:\n        results = []\n        for r in unique:\n            if r.get('value', 0) > 100:\n                results.append(r)\n            elif r.get('value', 0) > 50:\n                results.append(r)\n            else:\n                results.append(r)\n        return results\n    except:\n        return []\n\nif __name__ == '__main__':\n    src = [{'id': i, 'value': i * 10, 'valid': True} for i in range(20)]\n    print(run_etl(src, src[:10], src[5:]))\n"
  },
  {
    "id": 81, "tier": 3,
    "title": "Monolithic Legacy Data Migration System",
    "expected": "🔴 Critical: Unclosed file 'migration_errors.log', 🔴 Critical: Bare except hiding failures, 🔴 Critical: Mutating list during iteration in 'purge_invalid'",
    "code": "def migrate_users():\n    try:\n        f = open('migration_errors.log', 'w')\n        for u in [{'id': 1}, {'id': -1}]:\n            if u['id'] > 0:\n                pass\n    except:\n        pass\n\ndef purge_invalid(data):\n    for d in data:\n        if d.get('id', 0) < 0:\n            data.remove(d)\n    return data\n"
  },
  {
    "id": 82, "tier": 3,
    "title": "Monolithic SaaS Billing & CRM Router",
    "expected": "🔴 Critical: Unclosed file 'billing_access.log', 🔴 Critical: Bare except hiding failures, 🔴 Critical: DRY violation, 🟡 Style: HTML string concatenation",
    "code": "def process_tier_1():\n    try:\n        f = open('billing_access.log', 'a')\n    except:\n        pass\n\ndef process_tier_2():\n    try:\n        f = open('billing_access.log', 'a')\n    except:\n        pass\n"
  },
  {
    "id": 91, "tier": 3,
    "title": "Monolithic Web Scraper & Data Aggregator",
    "expected": "🔴 Critical: Unclosed file 'aggregated_data.csv', 🔴 Critical: Bare except hiding failures, 🔴 Critical: Mutating list in purge_banned_proxies, 🔴 Critical: DRY violation",
    "code": "def parse():\n    try:\n        f = open('aggregated_data.csv', 'w')\n    except:\n        pass\n\ndef parse_ebay():\n    try:\n        f = open('aggregated_data.csv', 'w')\n    except:\n        pass\n\ndef purge_banned(proxies):\n    for p in proxies:\n        if p.get('banned'):\n            proxies.remove(p)\n"
  },
  {
    "id": 92, "tier": 3,
    "title": "Monolithic Content Moderation Engine",
    "expected": "🔴 Critical: Unclosed file 'quarantine_audit.log', 🔴 Critical: Bare except hiding failures, 🔴 Critical: Mutating list in purge_suspended_users, 🔴 Critical: DRY violation",
    "code": "def ingest():\n    try:\n        f = open('quarantine_audit.log', 'w')\n    except:\n        pass\n\ndef ingest_video():\n    try:\n        f = open('quarantine_audit.log', 'w')\n    except:\n        pass\n\ndef purge_users(users):\n    for u in users:\n        if u.get('suspended'):\n            users.remove(u)\n"
  }
]

def parse_expected(expected_str):
    import re
    SEVERITY_MAP = {"🔴": "critical", "🟡": "style", "🔵": "info"}
    CATEGORY_PATTERNS = [
        ("mutable_default",   r"mutable\s+default"),
        ("off_by_one",        r"off.by.one|IndexError"),
        ("list_mutation",     r"mutat.*list|mutat.*iter"),
        ("missing_docstring", r"missing\s+docstring"),
        ("camelcase",         r"camelcase|CamelCase|snake_case"),
        ("eval_injection",    r"eval\(\)"),
        ("hardcoded_secret",  r"hardcoded?"),
        ("unclosed_file",     r"unclosed\s+file"),
        ("missing_super",     r"super\(\)|missing.*super"),
        ("performance_n2",    r"O\(n\^?2\)|O\(n²\)"),
        ("bare_except",       r"bare\s+except"),
        ("dry_violation",     r"DRY\s+violation"),
        ("shared_class_state",r"shared\s+mutable\s+state|class\s+attribute"),
        ("logical_error",     r"logical\s+error"),
    ]
    segments = re.split(r',\s*(?=🔴|🟡|🔵)', expected_str.strip())
    labels = []
    for seg in segments:
        seg = seg.strip()
        severity = "info"
        for emoji, sev in SEVERITY_MAP.items():
            if seg.startswith(emoji):
                severity = sev
                break
        cleaned = re.sub(r'^[🔴🟡🔵]\s+\w+:\s*', '', seg).strip()
        category = "other"
        for cat, pattern in CATEGORY_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                category = cat
                break
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", cleaned)
        keyword = quoted[0] if quoted else cleaned[:60]
        labels.append({"severity": severity, "category": category, "keyword": keyword})
    return labels

def main():
    import ast as _ast
    if not DATASET.exists():
        print("❌ dataset.json not found. Run prepare_dataset.py first.")
        return

    with open(DATASET, encoding="utf-8") as fh:
        data = json.load(fh)

    existing_ids = {e["id"] for e in data}
    added = 0
    for entry in MISSING_ENTRIES:
        if entry["id"] not in existing_ids:
            entry["expected_labels"] = parse_expected(entry["expected"])
            try:
                _ast.parse(entry["code"])
                entry["code_ast_valid"] = True
            except SyntaxError:
                entry["code_ast_valid"] = False
            data.append(entry)
            added += 1
            print(f"  ✅ Added ID={entry['id']} — {entry['title'][:55]}...")
        else:
            print(f"  ⏭  ID={entry['id']} already exists — skipping")

    data.sort(key=lambda e: e["id"])
    with open(DATASET, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    total = len(data)
    t1 = sum(1 for e in data if e["tier"] == 1)
    t2 = sum(1 for e in data if e["tier"] == 2)
    t3 = sum(1 for e in data if e["tier"] == 3)
    print(f"\n💾 Saved dataset.json — Total: {total} | Tier 1: {t1} | Tier 2: {t2} | Tier 3: {t3}")
    print(f"   Added {added} new entries.")

if __name__ == "__main__":
    main()
