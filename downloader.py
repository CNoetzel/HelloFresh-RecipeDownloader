import requests
from os import path
import logger
import datetime
import argparse

output_folder = 'pdf'
hello_fresh_gw_url = 'https://www.hellofresh.com/gw/'
access_token = None

argParser = argparse.ArgumentParser()
argParser.add_argument('--similaritySearch', action='store_true',
                       help='Enables the search for the recipe if it can\'t be downloaded checking your delivery history.')
argParser.set_defaults(similaritySearch=False)


def login():
    global access_token
    if not access_token:
        with open('.credentials', 'r', encoding='utf-8') as cred:
            access_token = cred.readline().strip()
            cred.close
    return access_token


headers = {
    'Authorization': f'Bearer {login()}'
}


def get_customer_data():
    # https://www.hellofresh.com/gw/api/customers/me/subscriptions
    response = requests.get(
        f'{hello_fresh_gw_url}api/customers/me/subscriptions', headers=headers)

    if not response.ok:
        logger.error(
            f'Request to retrieve subscription id failed with response: {response.status_code}')
    else:
        items = response.json().get('items')
        if items and len(items) > 0:
            id = items[0].get('id')
            locale = items[0].get('customer').get('locale')
            country = locale.split('-')[1] if locale else None
            return {'id': id, 'locale': locale, 'country': country}
        return None


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


def download_recipe(id, country, similaritySearch):
    # https://www.hellofresh.com/gw/recipes/recipes/62bb0448a27aacb4f0071e09
    response = requests.get(
        f'{hello_fresh_gw_url}recipes/recipes/{id}', headers=headers)

    if not response.ok:
        logger.error(
            f'Request recipe data for "{id}" failed with response: {response.status_code}')
    else:
        json = response.json()
        title = json.get("name")
        if is_already_downloaded(title):
            logger.info(
                f'Recipe "{title}" is already present, skipping download ...')
        else:
            slug = json.get("slug")
            ingredients = map(lambda i: i.get('name'), json.get('ingredients'))
            pdf_link = json.get("cardLink") or (similaritySearch and search_for_recipe(
                slug, title, ingredients, country))
            download_pdf(title, pdf_link)


def search_for_recipe(slug, title, ingredients, country):
    # https://www.hellofresh.de/gw/recipes/recipes/search?country=DE&locale=de-DE&q=Mediterraner%20Nudelsalat%20mit%20Halloumi&skip=0&take=16
    logger.info(
        f'SimilaritySearch enabled: Searching for recipe with title "{title}"')
    params = {
        'take': 20,
        'country': country,
        'q': title
    }
    response = requests.get(
        f'{hello_fresh_gw_url}recipes/recipes/search', params=params, headers=headers)

    if not response.ok:
        logger.error(
            f'Search for recipe with title "{title}" failed with response: {response.status_code}')
    else:
        for recipe in filter(lambda x: recipes_matches(x, slug, ingredients), response.json().get('items')):
            pdf_link = recipe.get('cardLink')
            if pdf_link:
                return pdf_link


def recipes_matches(recipe, compare_slug, compare_ingredients):
    # compare slug to avoid Thermomix recipes and ingredients to find matching recipes
    recipe_ingredients = map(lambda i: i.get(
        'name'), recipe.get('ingredients'))
    return recipe.get('slug') == compare_slug and set(recipe_ingredients) and set(compare_ingredients)


def download_pdf(title, pdf_url):
    if pdf_url:
        # https://hellofresh.com/recipecards/card/mini-conchiglie-mit-baconstreifen-und-babyspinat-6360f49afe52da0c720b57e4-88bb96f7.pdf
        response = requests.get(pdf_url)

        if (not response.ok):
            logger.error(
                f'Download for "{title}" failed with response: {response.status_code}')
            return
        else:
            logger.info(f'Successfully downloaded recipe "{title}"')
            with open(f'{output_folder}/{title}.pdf', 'wb') as out:
                out.write(response.content)
                out.close()
    else:
        logger.warn(f'No download URL given for recipe "{title}"')


def is_already_downloaded(recipe):
    return path.exists(f'./{output_folder}/{recipe}.pdf')


def main():
    args = argParser.parse_args()
    c_data = get_customer_data()
    logger.info(f'Customer data: {c_data}')
    today = datetime.date.today()
    if c_data:
        week = f'{today.year}-W{today.strftime("%V")}'
        list_of_recipes = set()
        get_deliveries_for_week(
            c_data.get('id'), week, list_of_recipes)
        logger.info(f'Collected {len(list_of_recipes)} recipes ...')
        for recipe_id in list_of_recipes:
            download_recipe(recipe_id, c_data.get('country'),
                            args.similaritySearch)
    else:
        logger.error(
            f'Subscription ID not present can not request received deliveries...')


if __name__ == "__main__":
    main()
