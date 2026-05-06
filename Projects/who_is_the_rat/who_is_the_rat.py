import requests
import urllib3
import os
import time
from dotenv import load_dotenv
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_id_to_check(session, strong_id, count, max_id):

    url = f"https://www.instagram.com/api/v1/friendships/{strong_id}/following/"

    params = { 
        "count": count,
        "max_id": max_id
    }

    try: 
        response = session.get(url, params=params, timeout=(10,20), verify=False)
        response.raise_for_status()
        print(f"Актуальный статус код: {response.status_code}")
    except requests.exceptions.ConnectTimeout:
        print(f"Connect timeout count: {count} max_id: {max_id}")
        return None
    except requests.exceptions.ReadTimeout:
        print(f"Read timeout count: {count} max_id: {max_id}")
        return None
    except requests.exceptions.RequestException:
        print(f"Request expetions count: {count} max_id: {max_id}")
        return None
    
    data = response.json()
    return data 

def check_follow_back(session, strong_id, user_id):

    url = f"https://www.instagram.com/api/v1/friendships/{strong_id}/following/"
    follow_back = False

    params = {
        "count": 50,
        "max_id": 0
    }


    try: 
        response = session.get(url, params=params, timeout=(10,20), verify=False)
        response.raise_for_status()
    except requests.exceptions.ConnectTimeout:
        print(f"Connect timeout count")
        return None
    except requests.exceptions.ReadTimeout:
        print(f"Read timeout")
        return None
    except requests.exceptions.RequestException:
        print(f"Request expetions count")
        return None
    
    data = response.json()
    for users in data["users"]:
        
        if users.get("strong_id__") == user_id:
            follow_back = True
            return follow_back
                
    return follow_back            

def get_env_varibales():

    load_dotenv()
    
    ig_id = os.getenv("ig_id")
    Cookie = os.getenv("Cookie")
    user_id = os.getenv("user_id")

    if not ig_id:
        raise ValueError("Ig_id is missing")
    if not Cookie:
        raise ValueError("Cookie is missing")
    if not user_id:
        raise ValueError("User_id is missing")
    
    return ig_id, Cookie, user_id


def main():

    start = time.perf_counter()  
    next_max_id = 0
    has_more = True
    follow_back_true = {}
    follow_back_false = {}
    ig_id, Cookie, user_id = get_env_varibales()

    with requests.Session() as session:
        session.headers.update({
            "x-ig-app-id": ig_id,
            "Cookie": Cookie
        })

        while has_more:
            
            data = get_id_to_check(session, user_id, 12, next_max_id)
            next_max_id = data.get("next_max_id")
            has_more = data.get("has_more")
            
            for users in data["users"]:
                strong_id__ = users.get("strong_id__")
                username = users.get("username")
                full_name = users.get("full_name")

                follow_back = check_follow_back(session, strong_id__, user_id)

                if follow_back:
                    follow_back_true[strong_id__] = {
                        "username": username,
                        "full_name": full_name,
                        "follow_back": follow_back
                        }
                else:
                    follow_back_false[strong_id__] = {
                        "username": username,
                        "full_name": full_name,
                        "follow_back": follow_back
                        }
                
            print(next_max_id, has_more)
    
    end = time.perf_counter()
    print((f"Код выполнился за {end - start:.4f} секунд"))
    print(f"Число подписок: {len(follow_back_false) + len(follow_back_true)}")
    print(f"Число взаимных подписок: {len(follow_back_true)}")
    print(f"Число не взаимных подписок: {len(follow_back_false)}")
    
    print(follow_back_false)

        
main()