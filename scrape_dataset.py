import asyncio
import json
import os

import dotenv
from tqdm import tqdm
from twscrape import API, gather
from twscrape.logger import set_log_level

async def recurse(current, api):
    try:
        tweet = await api.tweet_details(current['id'])  # Tweet
    except Exception as e:
        if 'Deleted status' in str(e):
            current['text'] = "[DELETED]"
        else:
            print(f"Tweet {current['id']} could not be fetched: {e}")
    else:
        if tweet is not None:
            current['text'] = tweet.rawContent
        else:
            print(f"Tweet {current['id']} could not be fetched")

    if current['children'] is not None:
        for i in current['children']:
            await recurse(i, api)

async def main():
    api = API()  # or API("path-to.db") – default is `accounts.db`

    # ADD ACCOUNTS (for CLI usage see next readme section)

    # Option 1. Adding account with cookies (more stable)
    usernames = [os.getenv("MAIN_X_USERNAME"), os.getenv("ALT_X_USERNAME")]
    await api.pool.delete_accounts(usernames)  # optional, to avoid duplicates
    main_cookies = os.getenv("MAIN_COOKIES")
    await api.pool.add_account(
        os.getenv("MAIN_X_USERNAME"), 
        os.getenv("MAIN_X_PASSWORD"), 
        os.getenv("MAIN_X_EMAIL"), 
        os.getenv("MAIN_X_EMAIL_PASSWORD"), 
        cookies=main_cookies
    )

    alt_cookies = os.getenv("ALT_COOKIES")
    await api.pool.add_account(
        os.getenv("ALT_X_USERNAME"), 
        os.getenv("ALT_X_PASSWORD"), 
        os.getenv("ALT_X_EMAIL"), 
        os.getenv("ALT_X_EMAIL_PASSWORD"), 
        cookies=alt_cookies
    )

    counter = await api.pool.login_all(usernames) # try to login to receive account cookies

    assert counter['success'] > 0, "No account could be logged in"

    this_dir_path = '.'
    for root_path, dirs, files in os.walk(this_dir_path):
        for filename in files:
            if not filename.endswith('.json'):
                continue

            if filename.endswith('_added_back.json'):
                continue

            print(f"Processing {filename}...")

            file_path = os.path.join(root_path, filename)
            txt_file_path = file_path.replace('.json', '_added_back.json')

            if os.path.exists(txt_file_path):
                continue
            
            with open(file_path) as f:
                a = json.load(f)

                # add text
                
                with open(txt_file_path, 'w') as output:
                    output.write("[")

                    children = []
                    current = None

                    final_id = a[-1]["root_tweet"]["id"]
                    for i in tqdm(a, desc="Tweets processed", unit=" tweets"):
                        root = i["root_tweet"]
                        if root["id"] == final_id:
                            await recurse(root, api)
                            json.dump(i, output)
                            output.write(']')
                        else:
                            await recurse(root, api)
                            json.dump(i, output)
                            output.write(',\n')
                        await asyncio.sleep(5)  # to avoid rate limits

if __name__ == "__main__":
    dotenv.load_dotenv()
    asyncio.run(main())