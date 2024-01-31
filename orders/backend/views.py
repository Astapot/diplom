import django_filters
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from .serializers import MyUserSerializer, ContactSerializer, OrderSerializer, OrderItemSerializer, \
    ProductInfoSerializer
from .models import MyUser, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Token, Contact, Order, \
    STATE_CHOICES, OrderItem
import yaml
from .validation import (check_yaml_partner, check_registration, check_login, check_delete,
                         validate_and_get_user, validate_data_contact, validate_confirmation_new_order)
from django.core.mail import send_mail
from django.conf import settings
import string


import bcrypt
import pdb
# pdb.set_trace()  (следующая строка - next)
import secrets


# Create your views here.



class MyUserRegistration(APIView):
    """
    post: - регистрирует польлзователя
    параметры : first_name, last_name, email, password, пароль хэшируется, по умолчанию пользователю выдается роль покупателя
    patch: принимает токен пользователя
    - изменяет данные о пользователе, тип пользователя может изменить только суперюзер
    delete: принимает токен пользователя
    удаляет пользователя по личному id или если токен суперюзера

    """
    def post(self, request):

        valid = check_registration(request.data)

        res = list(valid.values())[0]
        if res:
            password = bcrypt.hashpw(request.data['password'].encode(), bcrypt.gensalt()).decode()
            user = MyUser.objects.create(first_name=request.data['first_name'],
                                         password=password,
                                         last_name=request.data['last_name'],
                                         email=request.data['email'],
                                         )
            return JsonResponse({'you are registered': True})
        s = list(valid.keys())[0]
        return JsonResponse({s: False})


    def patch(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        # token = request.headers['Authorization'].split(' ')[1]
        # id = Token.objects.filter(token=token)[0]
        # user = MyUser.objects.filter(id=id.user_id)[0]
        # if not user:
        #     return JsonResponse({'only for': 'authorizated users'})


        if 'password' in request.data:
            password = bcrypt.hashpw(request.data['password'].encode(), bcrypt.gensalt()).decode()
            request.data['password'] = password

        if 'type' in request.data:
            if not user.is_superuser:
                return JsonResponse({'only admin': 'can patch type'})
            else:
                if 'user_id' not in request.data:
                    return JsonResponse({'give user_id': 'check data'})
                user_for_change = MyUser.objects.filter(id=request.data['user_id'])
                if not user_for_change:
                    return JsonResponse({f"user with id {request.data['user_id']}": "does not exist"})
                user_for_change = user_for_change[0]
                serializer = MyUserSerializer(user_for_change, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return JsonResponse({'user': f'{user_for_change.id} is patched'})

        serializer = MyUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'your account with id': f'{user.id} is patched'})
        return JsonResponse({'user id': 'not found'})

    def delete(self, request):
        valid = check_delete(request.headers, request.data)
        if valid:
            token = request.headers['Authorization'].split(' ')[1]
            user_id = request.data['user_id']
            object = Token.objects.filter(token=token)
            user = MyUser.objects.filter(id=object[0].user_id)[0]
            if object[0].user_id == user_id or user.is_superuser:
                MyUser.objects.filter(id=user_id).delete()
                return JsonResponse({'status': 'deleted'})
            return JsonResponse({'Only for owner': 'or admin'})

        return JsonResponse({'incorrect':'token or data'})



class UserLogin(APIView):
    """
    аутентификация пользователя:
    post: пользователь вводить емайл и пароль, ему в ответ присылается токен и id
    delete: принимает токен пользователя, если данные переданы верно - удаляет токен из базы данных

    """

    def post(self, request):
        valid = check_login(request.data)
        if list(valid.values())[0]:
            email = request.data['email']
            # password = bcrypt.hashpw(request.data['password'].encode(), bcrypt.gensalt()).decode()
            password = request.data['password'].encode()
            user = list(valid.keys())[0][0]
            # user = MyUser.objects.get(email=email)
            result = bcrypt.checkpw(password, user.password.encode())
            if result:
                token = Token.objects.filter(user_id=user.id)
                if token:
                    return JsonResponse({'your_token': str(token[0]),
                                         'your id': user.id
                                         },
                                        )
                token = secrets.token_urlsafe(16)
                res = Token.objects.filter(token=token) & Token.objects.exclude(user_id=user.id)
                while res:
                    token = token + secrets.token_urlsafe(16)
                    res = Token.objects.filter(token=token) & Token.objects.exclude(user_id=user.id)
                token_f = Token.objects.create(user_id=user.id, token=token)
                return JsonResponse({'your token': str(token_f),
                                     'your id': user.id
                                     })

        return JsonResponse({'incorrect': 'data'})



    def delete(self, request):
        valid = check_delete(request.headers, request.data)
        if valid:
            token = request.headers['Authorization'].split(' ')[1]
            user = request.data['user_id']
            Token.objects.filter(token=token).delete()
            return JsonResponse({'exit': 'success'})
        return JsonResponse({'incorrect':'data'})


class PartnerUpdate(APIView):
    """
    post: принимает токен магазина
    создает или обновляет магазин данного пользователя, а также товары в нем
    в параметрах передается название файла, лежащего в папке проекта

    """
    def post(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]

        if user.type != 'shop':
            return JsonResponse({'this func': 'only for shops'})

        file = (request.data['filename'])
        with open(file, encoding='utf-8') as ya:
            # data = yaml.load(ya, Loader=yaml.FullLoader)
            data = yaml.safe_load(ya)
            if check_yaml_partner(data):
                shop = data['shop']
                # user = MyUser.objects.get(id=1)
                shop = Shop.objects.get_or_create(name=shop, user_id=user.id)
                categories = data['categories']
                # Category.objects.all().delete()
                for cat in categories:
                    object = Category.objects.get_or_create(id=cat['id'],name=cat['name'])
                    object[0].shops.add(shop[0].id)
                goods = data['goods']
                ProductInfo.objects.filter(shop_id=shop[0].id).delete()
                for good in goods:
                    item = Product.objects.get_or_create(name=good['name'], category_id=good['category'])

                    product_info = ProductInfo.objects.create(product_id=item[0].id,
                                                              external_id=good['id'],
                                                              model=good['model'],
                                                              price=good['price'],
                                                              price_rrc=good['price_rrc'],
                                                              quantity=good['quantity'],
                                                              shop_id=shop[0].id)
                    ProductParameter.objects.filter(product_id=item[0].id).delete()
                    for parameter_name, value in good['parameters'].items():
                        param = Parameter.objects.get_or_create(name=parameter_name)
                        val = ProductParameter.objects.get_or_create(product_id=item[0].id, parameter_id=param[0].id, value=value)
                return JsonResponse({'status':'ok'})

            return JsonResponse({'yaml': 'incorrect'})


class ProductsView(APIView):
    """
    get: получение всех продуктов
    можно фильтровать по категориям, магазинам и имени(имя можно куском и в любом регистре)

    """
    def get(self, request):
        products = Product.objects.all()
        result = {}
        filters = request.query_params
        if filters.get("name"):
            name = filters['name']
            products_names = []
            for product in products:

                if name.casefold() in product.name.casefold():
                    products_names.append(product.name)
            products = Product.objects.none()
            for product_name in products_names:
                products = products | Product.objects.filter(name=product_name)  # слишком много операций
        if filters.get('category'):
            category = Category.objects.filter(name=filters['category'])
            if category:
                category = category[0]
                products = products & Product.objects.filter(category=category.id)
            else:
                products = []
        shop_f = filters.get('shop')
        for product in products:
            product_info = ProductInfo.objects.filter(product_id=product.id)
            if product_info:
                info = product_info[0]
                if shop_f and str(info.shop) != shop_f:
                    continue

                # print(product_info[0].model)
                name = product.name
                product_infos = product.product_infos.all()[0]
                # for i in product.product_infos.all():
                #     product_infos.append(str(i))
                # product_infos = ', '.join(product_infos)
                category = str(product.category)
                model = info.model
                price = info.price
                quantity = info.quantity
                shop = str(info.shop)
                parametrs = ProductParameter.objects.filter(product_id=product.id)
                params = {}
                for param in parametrs:
                    parameter = str(param.parameter)
                    value = param.value
                    params[parameter] = value
                result[name] = {
                    'product infos': str(product_infos),
                    'category': category,
                    'model': model,
                    'price': price,
                    'quantity': quantity,
                    'shop': shop,
                    'parameters': params
                                }
        #
        # print(request.query_params)
        return JsonResponse(result, json_dumps_params={'ensure_ascii': False})


class ProductDetailView(APIView):
    """

    get: выдает информацию о продукте, переданном в ссылке с помощью id
    """
    def get(self,request, id):
        product = Product.objects.filter(id=id)
        if product:
            product = product[0]
            product_info = ProductInfo.objects.filter(product_id=id)
            result = {}
            for info in product_info:
                name = product.name
                model = info.model
                price = info.price
                quantity = info.quantity
                shop = str(info.shop)
                parametrs = ProductParameter.objects.filter(product_id=product.id)
                params = {}
                for param in parametrs:
                    parameter = str(param.parameter)
                    value = param.value
                    params[parameter] = value
                result[name] = {
                    'model': model,
                    'price': price,
                    'quantity': quantity,
                    'provider': shop,
                    'parameters': params
                }
            return JsonResponse(result, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'this product': 'does not exist'})




class ContactView(APIView):
    """
    post: принимает токен покупателя или админа
    создает контакт пользователя

    get: принимает токен покупателя или админа
    выдает контакты пользователя

    patch: принимает токен покупателя или админа
    меняет контакт пользователя по id

    delete: принимает токен покупателя или админа
    удаляет контакт пользователя по id


    """
    # @staticmethod
    # def check_buyer(user):
    #     if user.type != 'buyer':
    #         return False
    #     return True

    def post(self, request):
        data = request.data
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'buyer' and not user.is_superuser:
            return JsonResponse({'this func': 'only for buyers'})
        data['user'] = user.id
        serializer = ContactSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({f'contact for user {user.email}': 'was added'})
        return JsonResponse(serializer.errors)


    def get(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'buyer' and not user.is_superuser:
            return JsonResponse({'this func': 'only for buyers'})
        queryset = Contact.objects.filter(user=user.id)
        data = ContactSerializer(queryset, many=True)
        return JsonResponse(data.data, safe=False)

    def patch(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'buyer' and not user.is_superuser:
            return JsonResponse({'this func': 'only for buyers'})
        check_data = validate_data_contact(request.data, user.id)
        if type(check_data) is dict:
            return JsonResponse(check_data)

        id = request.data.pop('id')
        contact = Contact.objects.filter(id=id)[0]
        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({f'contact with id {id} of user {user.email}': 'was patched'})
        return JsonResponse(serializer.errors)


    def delete(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'buyer' and not user.is_superuser:
            return JsonResponse({'this func': 'only for buyers'})
        check_data = validate_data_contact(request.data, user.id)
        if type(check_data) is dict:
            return JsonResponse(check_data)
        id = request.data['id']
        contact = Contact.objects.filter(id=id)[0].delete()
        return JsonResponse({f'contact with id {id} of user {user.email}': 'was deleted'})





class BasketView(APIView):
    """
    Работает с корзиной товаров пользователя с типом "покупатель"
    post: создает корзину, проверяет, что корзина одна, а пользователь - покупатель

    Параметры: contact - id, shop - id, token

    get: выдает информацию о заказе с типом "корзина" пользователю

    Параметры: token

    patch: позволяет изменять информацию о заказе, добавлять в него товары и изменять их количество
    проверяет, является ли пользователь покупателем, а тип товара - корзина
    Тип товара можно изменить только на "отмененный" или "новый"

    Параметры: order id - id, token
    необязательные:
        contact - id
        ordered items = [{"product_info": int,
                          "quantity": int
                            }]
        state: "new" or "canceled"
        Если тип заказа new то дополнительно отправляет на почту заказчику письмо с номером заказа и номером контакта
        для подтверждения

    delete: удаляет все заказы с типом корзина, у которых статус "отмененный"

    Можно выполнить, если пользователь - админ, или удаляет только корзину данного пользователя


    """


    def post(self, request):
        data = request.data
        data_for_valid = {'id': data.get('contact')}
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'buyer':
            return JsonResponse({'this function': 'only for buyers'})
        check_data = validate_data_contact(data_for_valid, user.id)
        if type(check_data) is dict:
            return JsonResponse(check_data)

        baskets = Order.objects.filter(user=user.id, state='basket')
        if baskets:
            return JsonResponse({'only 1 basket': 'for user'})
        data['user'] = user.id
        serializer = OrderSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors)

    def get(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'buyer':
            return JsonResponse({'this function': 'only for buyers'})
        queryset = Order.objects.filter(user=user.id, state='basket')
        data = OrderSerializer(queryset, many=True)
        if data.data:
            for num, i in enumerate(data.data[0]['ordered_items']):
                # pdb.set_trace()
                item = OrderItem.objects.filter(id=i)[0]
                product_info = item.product_info
                name = product_info.product
                shop = product_info.shop
                price = product_info.price
                quantity = item.quantity
                sum = quantity * price
                result = {
                    "name": str(name),
                    "shop": str(shop),
                    "price": price,
                    "quantity": quantity,
                    "sum": sum
                }
                # info = ProductInfo.objects.filter(id=str(product_info))[0]
                data.data[0]['ordered_items'][num] = result

        return JsonResponse(data.data, safe=False, json_dumps_params={'ensure_ascii': False})

    def patch(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'buyer':
            return JsonResponse({'this function': 'only for buyers'})
        order_id = request.data.get('order_id')
        if not order_id:
            return JsonResponse({'give': 'order_id'})
        order = Order.objects.filter(id=order_id, user=user.id)
        if not order:
            return JsonResponse({'this order not yours': 'or does not exists'})
        order = order[0]
        old_state = order.state
        if order.state != 'basket':
            return JsonResponse({'this function only for': f'BASKET, but your order is {order.state.upper()}'})
        state = request.data.get('state')
        contact = request.data.get('contact')
        ordered_items = request.data.get('ordered_items')
        if state:
            if state not in ['canceled', 'new', 'basket']:
                return JsonResponse({f'u can change only': 'CANCELED or NEW'})

        if contact:
            data_for_validate = {'id': contact}
            result = validate_data_contact(data_for_validate, user.id)
            if type(result) is dict:
                return JsonResponse(result)

        #валидаация для предметов в заказе
        if ordered_items:
            request.data.pop('ordered_items')
            if type(ordered_items) is not list:
                return JsonResponse({'ordered_items': 'must be a dicts in list'})
            else:
                if type(ordered_items[0]) is not dict:
                    return JsonResponse({'ordered_items': 'must be a dicts in list'})


            for item in ordered_items:
                product_info = item.get('product_info')
                if not product_info:
                    return JsonResponse({'check PRODUCT_INFO': 'in ordered items'})
                if item.get('assembled'):
                    return JsonResponse({'assembled status': 'available for change only during assembly'})
                it = ProductInfo.objects.filter(id=product_info)
                if not it:
                    return JsonResponse({'check PRODUCT_INFO': 'this id does not exist'})
                it = it[0]
                q = item.get('quantity')
                if not q:
                    return JsonResponse({'check QUANTITY': 'in ordered items'})
                if type(q) != int or q <= 0:
                    return JsonResponse({'QUANTITY': 'is positive integer! Check data'})
                if q > it.quantity:
                    return JsonResponse({f'u can order maximum {it.quantity} things': f'for product {it} ({it.product})'}, json_dumps_params={'ensure_ascii': False})

            #создание\обновление предметов в заказе
            for item in ordered_items:
                item['order'] = order.id
                object = OrderItem.objects.filter(order=order.id, product_info=item['product_info'])

                if object:
                    serializer = OrderItemSerializer(object[0], data=item, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                else:
                    # pdb.set_trace()
                    serializer = OrderItemSerializer(data=item)
                    if serializer.is_valid():
                        serializer.save()
                    else:
                        return JsonResponse(serializer.errors)

        #обновление заказа
        serializer_order = OrderSerializer(order, data=request.data, partial=True)
        if serializer_order.is_valid():
            serializer_order.save()
        if request.data.get('state') == 'new' and old_state == 'basket':
            subject = "Change order state"
            # code = ''.join(secrets.choice(string.digits) for i in range(6))
            # NewOrderCodes.objects.create(user=user.id, order=order.id, code=code)
            message = f"Your order state changed to 'NEW', to confirm use order_id: {order_id}, contact_id {contact}"

            send_mail(subject=subject, message=message, from_email=settings.EMAIL_HOST_USER, recipient_list=[user.email],
                      fail_silently=False, )

        return JsonResponse({f'order with id {order.id}': 'was patched successfully'})

    def delete(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.is_superuser:
            orders = Order.objects.filter(state='canceled').delete()
            return JsonResponse({'orders with state "CANCELED"': 'were deleted'})
        orders = Order.objects.filter(state='canceled', user=user.id).delete()
        return JsonResponse({'your orders with state canceled': 'were deleted'})

# доделать патч и делет
class ConfirmationView(APIView):
    """
    Класс для работы с завершенными корзинами пользователя

    get: принимает token

    выдает заказы со статусом new

    post:

    параметры: contact_id , order_id
    Подтверждает заказ и меняет статус заказа на 'confirmed'

    patch:

    параметры: contact_id , order_id, state : 'canceled' или 'basket'
    При наличии данных параметров изменяет статус заказа на соответствующий

    delete:

    Удаляет все заказы со статусом canceled из базы данных если токен пользователя суперюзер

    Удаляет личные заказы со статусом canceled из базы данных если токен покупателя


    """

    def get(self, request):
        answer = validate_and_get_user(request.headers)
        result = []
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'buyer':
            return JsonResponse({'this function': 'only for buyers'})
        orders = Order.objects.filter(state='new', user=user.id)
        for order in orders:
            result_items = []
            for i in order.ordered_items.all():
                product_info = i.product_info
                name = product_info.product
                shop = product_info.shop
                price = product_info.price
                quantity = i.quantity
                sum = quantity * price
                res = {
                    "name": str(name),
                    "shop": str(shop),
                    "price": price,
                    "quantity": quantity,
                    "sum": sum
                }
                result_items.append(res)
            result.append({str(order): result_items})
        return JsonResponse({'NEW orders': result}, json_dumps_params={'ensure_ascii': False})


    def post(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'buyer':
            return JsonResponse({'this function': 'only for buyers'})
        validation = validate_confirmation_new_order(request.data)
        if type(validation) is dict:
            return JsonResponse(validation)
        order_id = request.data['order_id']
        contact_id = request.data['contact_id']
        order = Order.objects.filter(id=order_id, state='new')

        if not order:
            return JsonResponse({'this order': 'does not exist or not NEW'})
        order = order[0]
        if order.user != user:
            return JsonResponse({'this order': 'not yours'})
        if contact_id != order.contact.id:
            return JsonResponse({'wrong contact_id': 'check data'})
        serializer = OrderSerializer(order, data={'state': 'confirmed'}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({str(order): 'is confirmed'})
        return JsonResponse(serializer.errors)

    def patch(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'buyer':
            return JsonResponse({'this function': 'only for buyers'})
        validation = validate_confirmation_new_order(request.data)

        if type(validation) is dict:
            return JsonResponse(validation)
        order_id = request.data['order_id']
        contact_id = request.data['contact_id']
        order = Order.objects.filter(id=order_id, state='new')


        if not order:
            return JsonResponse({'this order': 'does not exist or not NEW'})
        order = order[0]
        if order.user != user:
            return JsonResponse({'this order': 'not yours'})
        if contact_id != order.contact.id:
            return JsonResponse({'wrong contact_id': 'check data'})
        # if request.data.get('test'):
        #     code_test = ''.join(secrets.choice(string.digits) for i in range(6))
        #     NewOrderCodes.objects.create(user=user, order=order, code=code_test)
        # check_code = NewOrderCodes.objects.filter(user=user.id, order=order.id, code=code)
        # if not check_code:
        #     return JsonResponse({'wrong code': 'check data'})
        if request.data.get('state') == 'canceled':
            serializer = OrderSerializer(order, data={'state': 'canceled'}, partial=True)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({str(order): 'is canceled'})
        if request.data.get('state') == 'basket':
            serializer = OrderSerializer(order, data={'state': 'basket'}, partial=True)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({str(order): 'is basket now'})

        return JsonResponse({str(order): 'did nothing', 'this func can only change state': 'CANCELED or BASKET'})

    def delete(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.is_superuser:
            orders = Order.objects.filter(state='canceled').delete()
            return JsonResponse({'orders with state "CANCELED"': 'were deleted'})
        orders = Order.objects.filter(state='canceled', user=user.id).delete()
        return JsonResponse({'your orders with state canceled': 'were deleted'})


class AssembleView(APIView):
    """
    get: принимает токен продавца
    Выдает ордера с товарами, которые принадлежат магазинам пользователя, запрашивающего ордера

    post: принимает токен продавца
    параметры: order_id

    меняет параметр assembled у товаров в заказе на True (только у тех, которые принадлежат данным магазинам)
    Если после обновления все товары в заказе приобрели такой статус, то order state меняется на assembled

    patch: принимает токен суперюзера
    параметры: order_id, state: canceled
    Если все правильно меняет статус заказа на отмененный и отправляет письмо об этом на почту владельцу заказа

    delete: принимает токен суперюзера или покупателя
    Если токен суперюзера - удаляет все заказы со статусом canceled
    Если токен покупателя - удаляет его заказы со статусом canceled


    """

    def get(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'shop':
            return JsonResponse({'this function': 'only for shop'})
        orders = Order.objects.filter(state='confirmed')
        if not orders:
            return JsonResponse({'no work for you': 'no CONFIRMED orders!'})
        confirmed_orders = []
        for order in orders:
            order_items = []
            for item in order.ordered_items.all():
                if item.assembled:
                    continue
                product_info = item.product_info
                if product_info.shop in user.shops.all():
                    product_id = product_info.id
                    name = product_info.product
                    shop = product_info.shop
                    price = product_info.price
                    quantity = item.quantity
                    assembled = item.assembled
                    res = {
                        "id": product_id,
                        "name": str(name),
                        "shop": str(shop),
                        "price": price,
                        "quantity": quantity,
                        "assembled": assembled
                    }
                    order_items.append(res)
            if order_items:
                confirmed_orders.append({str(order): order_items})
        return JsonResponse({'CONFIRMED orders': confirmed_orders}, json_dumps_params={'ensure_ascii': False})

    def post(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'shop':
            return JsonResponse({'this function': 'only for shop'})
        shops = user.shops.all()
        order_id = request.data.get('order_id')
        order = Order.objects.filter(id=order_id)
        if not order:
            return JsonResponse({f'order with id {order_id}': 'does not exist'})
        order = order[0]
        if order.state != 'confirmed':
            return JsonResponse({'this func': 'for CONFIRMED orders'})
        ordered_items = order.ordered_items.all()

        # валидация предметов в заказе по количеству
        for item in ordered_items:
            product_info = item.product_info
            shop = product_info.shop
            if shop in shops:
                store_product = ProductInfo.objects.filter(id=product_info.id)
                if not store_product:
                    return JsonResponse({f'product with id {product_info.id} does not exist': 'call admin'})
                store_product = store_product[0]
                product_q = store_product.quantity
                item_q = item.quantity
                if item_q > product_q:
                    return JsonResponse({f'there is not enough product in shop {shop}': 'call admin to cancel or change order'}, json_dumps_params={'ensure_ascii': False})

        #изменение статуса предмета в заказе на собран + изменение количества на складе
        result_items = []
        for item in ordered_items:
            product_info = item.product_info
            shop = product_info.shop
            if shop in shops:
                if item.assembled:
                    continue
                name = product_info.product
                shop = product_info.shop
                price = product_info.price
                quantity = item.quantity
                res = {
                    "id": product_info.id,
                    "name": str(name),
                    "shop": str(shop),
                    "price": price,
                    "quantity": quantity
                }
                result_items.append(res)

                store_product = ProductInfo.objects.filter(id=product_info.id)[0]
                product_q = store_product.quantity
                product_serializer = ProductInfoSerializer(item.product_info, data={'quantity': product_q - quantity}, partial=True)
                if product_serializer.is_valid():
                    product_serializer.save()
                serializer = OrderItemSerializer(item, data={'assembled': True}, partial=True)
                if serializer.is_valid():
                    serializer.save()

        for item in ordered_items:
            if not item.assembled:
                break
        else:
            serializer_order = OrderSerializer(order, data={'state': 'assembled'}, partial=True)
            if serializer_order.is_valid():
                serializer_order.save()
                return JsonResponse({str(order): 'was assembled'})
            return JsonResponse(serializer.errors)
        return JsonResponse({'assembled items': result_items}, json_dumps_params={'ensure_ascii': False})

    def patch(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if not user.is_superuser:
            return JsonResponse({'only admin can cancel confirmed order': 'call admin'})
        # if user.type != 'shop':
        #     return JsonResponse({'this function': 'only for shop'})


        order_id = request.data.get('order_id')
        if not order_id:
            return JsonResponse({'give order_id': 'check data'})
        state = request.data.get('state')
        if not state:
            return JsonResponse({'this func change state': 'give state'})
        order = Order.objects.filter(id=order_id)

        if not order:
            return JsonResponse({f'order with id {order_id}': 'does not exist'})
        order = order[0]
        if order.state != 'confirmed':
            return JsonResponse({'this func': 'for CONFIRMED orders'})
        if state != 'canceled':
            return JsonResponse({'this func change state': 'only on CANCELED'})

        #возвращение товара насклад, если он был собран
        for item in order.ordered_items.all():
            if item.assembled:
                product_info = item.product_info
                product_serializer = ProductInfoSerializer(product_info, data={'quantity': product_info.quantity + item.quantity}, partial=True)
                if product_serializer.is_valid():
                    product_serializer.save()
                orderitem_serializer = OrderItemSerializer(item, data={'assembled': False}, partial=True)
                if orderitem_serializer.is_valid():
                    orderitem_serializer.save()


        serializer = OrderSerializer(order, data={'state': 'canceled'}, partial=True)
        if serializer.is_valid():
            subject = "Change order state"
            message = (
                f"Your {str(order)} state changed to 'CANCELED' by user {user.username} ({', '.join([str(shop) for shop in user.shops.all()])}), if something"
                f" wrong - contact us")

            send_mail(subject=subject, message=message, from_email=settings.EMAIL_HOST_USER,
                      recipient_list=[order.user.email],
                      fail_silently=False, )
            serializer.save()

            # message = (f"Your {str(order)} state changed to 'CANCELED' by user {user.username} ({user.shops.all()}), if something"
            #            f"wrong - contact us")
            #
            # send_mail(subject=subject, message=message, from_email=settings.EMAIL_HOST_USER,
            #           recipient_list=[order.user.email],
            #           fail_silently=False, )
            return JsonResponse({str(order): 'change state', 'state': 'CANCELED'})

    def delete(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.is_superuser:
            orders = Order.objects.filter(state='canceled').delete()
            return JsonResponse({'orders with state "CANCELED"': 'were deleted'})
        orders = Order.objects.filter(state='canceled', user=user.id).delete()
        return JsonResponse({'your orders with state canceled': 'were deleted'})














