import json
import requests
from pathlib import Path

from tweet_parser import TweetParser

class TweetDownloader():

    def __init__(self):
        # Load in user specific data from config.json file
        with open("config.json") as json_data_file:
            self.config_data = json.load(json_data_file)
            self.twitter_user_id = self.config_data.get('USER_ID')
            self.header_authorization = self.config_data.get('HEADER_AUTHORIZATION')
            self.header_cookie = self.config_data.get('HEADER_COOKIES')
            self.header_csrf = self.config_data.get('HEADER_CSRF')
            self.output_json_file_path = Path(self.config_data.get('OUTPUT_JSON_FILE_PATH'))
            self.tweet_stop_id = self.config_data.get("TWEET_STOP_ID")

    def retrieve_all_likes(self):
        all_tweets = []

        likes_page = self.retrieve_likes_page()
        page_cursor = self.get_cursor(likes_page)
        old_page_cursor = None
        current_page = 1

        while likes_page and page_cursor and page_cursor != old_page_cursor:
            print(f"Fetching likes page: {current_page}...")
            current_page += 1
            stop = False
            for raw_tweet in likes_page:
                try:
                    tweet_parser = TweetParser(raw_tweet)
                    if tweet_parser.is_valid_tweet:
                        if self.tweet_stop_id and tweet_parser.tweet_id == str(self.tweet_stop_id):
                            stop = True
                            break
                        else:
                            all_tweets.append(tweet_parser.tweet_as_json())
                except KeyError:
                    # TODO: We should have an option to dump such tweet structures.
                    pass # Ignore tweets that are not of interest to us.
            if stop:
                break
            old_page_cursor = page_cursor
            likes_page = self.retrieve_likes_page(cursor=page_cursor)
            page_cursor = self.get_cursor(likes_page)

        if all_tweets:
            output_file = self.output_json_file_path
            if output_file.exists():
                parent_dir = output_file.parent
                name_toks = output_file.stem.split(".")
                num_tok = len(name_toks) > 1 and name_toks[-1].isnumeric() and name_toks[-1] or None
                next_num = num_tok and int(num_tok) or 0
                base_name_toks = num_tok and name_toks[:-1] or name_toks
                while True:
                    next_num += 1
                    output_file = Path(parent_dir, ".".join(base_name_toks + [str(next_num)]) + output_file.suffix)
                    if not output_file.exists():
                        break
            with open(output_file, 'w') as f:
                f.write(json.dumps(all_tweets))
            print(f'Done. JSON with {len(all_tweets)} liked tweets saved to: {output_file}')

            self.config_data["TWEET_STOP_ID"] = all_tweets[0]["tweet_id"]
            with open("config.json", "w") as fout:
                json.dump(self.config_data, fout, sort_keys=True, indent=4)

        else:
            print("No new tweets found")

    def retrieve_likes_page(self, cursor=None):
        likes_url = 'https://api.twitter.com/graphql/QK8AVO3RpcnbLPKXLAiVog/Likes'
        variables_data_encoded = json.dumps(self.likes_request_variables_data(cursor=cursor))
        features_data_encoded = json.dumps(self.likes_request_features_data())
        response = requests.get(
            likes_url,
            params={"variables": variables_data_encoded, "features": features_data_encoded},
            headers=self.likes_request_headers()
        )
        return self.extract_likes_entries(response.json())

    def extract_likes_entries(self, raw_data):
        return raw_data['data']['user']['result']['timeline_v2']['timeline']['instructions'][0]['entries']

    def get_cursor(self, page_json):
        return page_json[-1]['content']['value']

    def likes_request_variables_data(self, cursor=None):
        variables_data = {
            "userId": self.twitter_user_id,
            "count": 100,
            "includePromotedContent": False,
            "withSuperFollowsUserFields": False,
            "withDownvotePerspective": False,
            "withReactionsMetadata": False,
            "withReactionsPerspective": False,
            "withSuperFollowsTweetFields": False,
            "withClientEventToken": False,
            "withBirdwatchNotes": False,
            "withVoice": False,
            "withV2Timeline": True
        }
        if cursor:
            variables_data["cursor"] = cursor
        return variables_data

    def likes_request_headers(self):
        return {
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Authorization': self.header_authorization,
            'Accept-Language': 'en-US,en;q=0.9',
            'Host': 'api.twitter.com',
            'Origin': 'https://twitter.com',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Referer': 'https://twitter.com/',
            'Connection': 'keep-alive',
            'Cookie': self.header_cookie,
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': 'en',
            'x-csrf-token': self.header_csrf,
            'x-twitter-auth-type': 'OAuth2Session'
        }

    def likes_request_features_data(self):
        return {
            "responsive_web_twitter_blue_verified_badge_is_enabled": True,
            "verified_phone_label_enabled": False,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "view_counts_public_visibility_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": False,
            "tweetypie_unmention_optimization_enabled": True,
            "responsive_web_uc_gql_enabled": True,
            "vibe_api_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": False,
            "interactive_text_enabled": True,
            "responsive_web_text_conversations_enabled": False,
            "responsive_web_enhance_cards_enabled": False
        }

if __name__ == '__main__':
    downloader = TweetDownloader()
    print(f'Starting retrieval of likes for Twitter user {downloader.twitter_user_id}...')
    downloader.retrieve_all_likes()
