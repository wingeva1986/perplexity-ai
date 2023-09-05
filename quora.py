import sys
import os
import poe
import time
import requests
#import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

proxy={'https':'http://127.0.0.1:7890'}

# you can type your email here or pass it as an argument
'''
if len(sys.argv) > 1:
    email = sys.argv[1]
else:
    email = input("Enter your email: ")
'''

options = webdriver.ChromeOptions()
#options.add_argument("--headless") # !uncomment when done testing
options.add_argument("start-maximized")
#options.add_experimental_option("excludeSwitches", ["enable-automation"])
#options.add_experimental_option('useAutomationExtension', False)
#driver = uc.Chrome(options=options)

options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_experimental_option('useAutomationExtension', False) 
s=Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=s, options=options)

stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
)

#driver = webdriver.Chrome(options=options)

# Step # | name | target | value
driver.get("https://quora.com")
print(driver.title)
assert "Quora" in driver.title
print("Page opened successfully.")

driver.set_window_size(802, 816)

driver.find_element(By.CSS_SELECTOR, ".base___StyledClickWrapper-lx6eke-1").click()
print("Clicked on signup with mail.")
time.sleep(2)


driver.find_element(By.ID, "profile-name").click()
print("Clicked on nikname box.")
time.sleep(2)

driver.find_element(By.ID, "email").click()
print("Clicked on email box.")
time.sleep(2)

#get an email
res=requests.get('https://task.cnvercel.eu.org/getmail',proxies=proxy).json()
email=res["mail"]
print(email)

driver.find_element(By.ID, "email").send_keys(email)
print("Email entered successfully.")
time.sleep(5)



driver.find_element(By.ID, "confirmation-code").click()
print("Clicked on 6-digit box.")
time.sleep(5)

while True:
    res=requests.get('https://task.cnvercel.eu.org/poeyzm/'+email,proxies=proxy).json()
    print(res)
    if "yzm" in res:
        code= res["yzm"]
        print(code)
        if len(code) == 6 and code.isdigit():
            break
    time.sleep(2)
'''
while True:
    code = input("Check your email and enter the verification code: ")
    if len(code) == 6 and code.isdigit():
        break
    print("Invalid verification code. Please enter a 6-digit number.")
'''

driver.find_element(By.ID, "confirmation-code").send_keys(code)
print("Verification code entered successfully.")
time.sleep(20)



# Get token and save to a file
token = None
script_dir = os.path.dirname(os.path.abspath(__file__))
token_path = os.path.join(script_dir,  "quora_token.txt")

try:
    token = driver.get_cookie("m-b")["value"]
    with open(token_path, "a") as f:
        f.write(token+'\n')
    print("Token saved successfully in poe_token.txt.")
except Exception as e:
    print("Error occurred while retrieving or saving the token:", str(e))

'''
try:
    client = poe.Client(token)
    print("token:", token)
    print("Login successful. Bots available:", client.get_bot_names())
except RuntimeError as e:
    print(e)
    print("try generating manually.")
'''

driver.close()
