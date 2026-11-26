#!/usr/bin/env python3
"""Interactive Gothic Narrative Game"""
import urllib.request
import json

BASE = "http://localhost:8000"

def api_get(path):
    resp = urllib.request.urlopen(f"{BASE}{path}")
    return json.loads(resp.read().decode())

def api_post(path):
    req = urllib.request.Request(f"{BASE}{path}", method='POST')
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode())

def play():
    print("\n🕷️  GOTHIC NARRATIVE ENGINE  🕷️")
    print("="*50)
    
    scene = api_get("/story/start")
    
    while not scene.get("is_ending"):
        print(f"\n{'='*50}")
        print(f"**{scene['title']}**")
        print(f"{'='*50}")
        print(scene['description'])
        print()
        
        for i, c in enumerate(scene['choices'], 1):
            print(f"  [{i}] {c['text']}")
        
        try:
            choice_idx = int(input("\nYour choice: ")) - 1
            if choice_idx < 0 or choice_idx >= len(scene['choices']):
                print("Invalid choice, try again.")
                continue
                
            choice_id = scene['choices'][choice_idx]['id']
            current = scene['id']
            
            scene = api_post(f"/story/choose?choice_id={choice_id}&current_scene={current}")
        except (ValueError, IndexError):
            print("Invalid input, try again.")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            return
    
    print(f"\n{'='*50}")
    ending = scene.get('ending_type', 'THE END')
    if ending == "good":
        print("✨ GOOD ENDING - YOU ESCAPED! ✨")
    elif ending == "bad":
        print("💀 BAD ENDING - YOU ARE DOOMED 💀")
    else:
        print(f"*** {ending.upper()} ***")
    print(f"{'='*50}")
    print(scene['description'])
    print()

if __name__ == "__main__":
    play()
