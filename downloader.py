import requests
from os import path
import logger
import datetime

output_folder = 'pdf'
hello_fresh_gw_url = 'https://www.hellofresh.com/gw/'
access_token = None


def login():
    global access_token
    if not access_token:
        with open('.credentials', 'r', encoding='utf-8') as cred:
            access_token = cred.readline()
            cred.close
    return access_token


headers = {
    'Authorization': f'Bearer {login()}'
}


def get_subscription_id():
    # https://www.hellofresh.com/gw/api/customers/me/subscriptions
    response = requests.get(
        f'{hello_fresh_gw_url}api/customers/me/subscriptions', headers=headers)

    if not response.ok:
        logger.error(
            f'Request to retrieve subscription id failed with response: {response.status_code}')
    else:
        json = response.json()
        return json.get('items')[0].get('id') if len(json.get('items')) > 0 else None


def get_deliveries_for_week(subscription_id: str, week: str, list_of_recipes: set):
    # https://www.hellofresh.com/gw/my-deliveries/past-deliveries?subscription=xxxxxxx&from=2022-W52
    params = {
        'subscription': subscription_id,
        'from': week
    }
    response = requests.get(
        f'{hello_fresh_gw_url}my-deliveries/past-deliveries', params=params, headers=headers)

    if not response.ok:
        logger.error(
            f'Request to retrieve past deliveries failed with response: {response.status_code}')
    else:
        json = response.json()
        for delivery in json.get('weeks'):
            for meal in delivery.get('meals'):
                list_of_recipes.add(meal.get('id'))
        next_week = json.get('nextWeek')
        if next_week:
            return get_deliveries_for_week(subscription_id, next_week, list_of_recipes)


def download_recipe(id):
    # https://www.hellofresh.com/gw/recipes/recipes/62bb0448a27aacb4f0071e09
    response = requests.get(
        f'{hello_fresh_gw_url}recipes/recipes/{id}', headers=headers)

    if not response.ok:
        logger.error(
            f'Request recipe data for "{id}" failed with response: {response.status_code}')
    else:
        json = response.json()
        title = json.get("name")
        pdf_link = json.get("cardLink")
        if not is_already_downloaded(title):
            download_pdf(title, pdf_link)
        else:
            logger.info(
                f'Recipe "{title}" is already present, skipping download ...')


def download_pdf(title, pdf_url):
    if pdf_url:
        # https://hellofresh.com/recipecards/card/mini-conchiglie-mit-baconstreifen-und-babyspinat-6360f49afe52da0c720b57e4-88bb96f7.pdf
        response = requests.get(pdf_url, headers=headers)

        if (not response.ok):
            logger.error(
                f'Download for "{title}" failed with response: {response.status_code}')
            return
        else:
            logger.info(f'Sucessfully downloaded recipe "{title}"')
            with open(f'{output_folder}/{title}.pdf', 'wb') as out:
                out.write(response.content)
                out.close()
    else:
        logger.warn(f'No download URL given for recipe "{title}"')


def is_already_downloaded(recipe):
    return path.exists(f'./{output_folder}/{recipe}.pdf')


def main():
    subscription_id = get_subscription_id()
    today = datetime.date.today()
    if subscription_id:
        week = f'{today.year}-W{today.strftime("%V")}'
        list_of_recipes = set()
        get_deliveries_for_week(subscription_id, week, list_of_recipes)
        logger.info(f'Collected {len(list_of_recipes)} recipes ...')
        for recipe_id in list_of_recipes:
            download_recipe(recipe_id)
    else:
        logger.error(
            f'Subscription ID not present can not request received deliveries...')


if __name__ == "__main__":
    main()
