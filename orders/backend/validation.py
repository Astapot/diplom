from .models import MyUser, Token, Contact
import pdb
# pdb.set_trace()
def check_yaml_partner(yaml_file):

    array_of_keys = ['shop', 'categories', 'goods']
    item_params = ['id', 'parameters', 'model', 'name', 'category', 'price', 'price_rrc', 'quantity']
    cat_params = ['id', 'name']
    keys = yaml_file.keys()
    for key in array_of_keys:
        if key in yaml_file:
            continue
        return False

    for param in item_params:
        for good in yaml_file['goods']:
            if param in good:
                continue
            return False
    for param in cat_params:
        for category in yaml_file['categories']:
            if param in category:
                continue
            return False
    return True


def check_registration(data):
    array_of_data = ['first_name', 'last_name', 'password', 'email']
    for word in array_of_data:
        if word not in data:
            return {f'check {word} in your data!': False}
    uniq = MyUser.objects.filter(email=data['email'])
    if uniq:
        return {f'{data["email"]} already exists': False}
    return {'all right': True}


def check_login(data):
    array_of_data = ['email', 'password']
    for word in array_of_data:
        if word not in data:
            return {f'{word} must be in request!': False}
    user = MyUser.objects.filter(email=data['email'])
    if not user:
        return {f'user with email {data["email"]} does not exist' : False}
    return {user : True}


def check_delete(headers, data):
    if list(Token.objects.filter(token=headers.get('Authorization').split(' ')[1])) and type(data.get('user_id')) is int:
        return True
    return False


def validate_and_get_user(headers) -> MyUser:
    """
    Returns MyUser.object with TRUE value

    or

    string if incorrect data
    """
    if not headers.get('Authorization'):
        return 'only for authorizated'
    token_form = headers['Authorization'].split(' ')
    if len(token_form) != 2:
        return 'incorrect token form'
    token = token_form[1]
    token_object = Token.objects.filter(token=token)
    if not token_object:
        return 'this user is not authorizated'
    user_id = token_object[0].user_id
    user = MyUser.objects.filter(id=user_id)[0]
    return {user: True}


def validate_data_contact(data, user_id):
    """
    validate keyword id in data
    :param data: request.data, user.id
    :return: True if validated, False if not
    """

    id = data.get('id')
    if id:
        contact = Contact.objects.filter(id=id)
        if not contact:
            return {f'contact with id {id}': 'does not exist'}
        contacts = Contact.objects.filter(user=user_id)
        contacts_ids = []
        for c in contacts:
            contacts_ids.append(c.id)
        if int(id) not in contacts_ids:
            return {'this id': 'is not your contact'}
        return True
    return {'no id': 'in data'}

