import django_filters
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from .serializers import MyUserSerializer, ContactSerializer, OrderSerializer, OrderItemSerializer
from .models import MyUser, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Token, Contact, Order, \
    STATE_CHOICES, OrderItem
import yaml
from .validation import (check_yaml_partner, check_registration, check_login, check_delete,
                         validate_and_get_user, validate_data_contact)

import bcrypt
import pdb
# pdb.set_trace()  (следующая строка - next)
import secrets


# Create your views here.
# class MyUserViewSet(ModelViewSet):
#     queryset = MyUser.objects.all()
#     serializer_class = MyUserSerializer


class MyUserRegistration(APIView):
    def post(self, request):
        print(request.data)

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
        token = request.headers['Authorization'].split(' ')[1]
        id = Token.objects.filter(token=token)[0]
        user = MyUser.objects.filter(id=id.user_id)[0]
        if not user:
            return JsonResponse({'only for': 'authorizated users'})

        if 'password' in request.data:
            password = bcrypt.hashpw(request.data['password'].encode(), bcrypt.gensalt()).decode()
            request.data['password'] = password

        if 'type' in request.data:
            if not user.is_superuser:
                return JsonResponse({'only admin': 'can patch type'})

        serializer = MyUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'user': f'{user.id} is patched'})
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
        queryset = Contact.objects.filter(user=user.id)
        data = ContactSerializer(queryset, many=True)
        return JsonResponse(data.data, safe=False)

    def patch(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
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
    проверяет, является ли пользователь покупателем, а тип товара - корзина, также если товары из разных магазинов,
    то не позволяет обновить ордер
    Тип товара можно изменить только на "отмененный" или "новый"

    Параметры: order id - id, token
    необязательные:
        contact - id
        ordered items = [{"product_info": int,
                          "quantity": int
                            }]

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

        if ordered_items:
            request.data.pop('ordered_items')
            if type(ordered_items) is not list:
                return JsonResponse({'ordered_items': 'must be a dicts in list'})
            else:
                if type(ordered_items[0]) is not dict:
                    return JsonResponse({'ordered_items': 'must be a dicts in list'})

            shop = order.shop

            for item in ordered_items:
                if not item.get('product_info'):
                    return JsonResponse({'check PRODUCT_INFO': 'in ordered items'})
                s = ProductInfo.objects.filter(id=item['product_info'])
                if s:
                    s = s[0].shop
                    if shop != s:
                        return JsonResponse({'u can choose products': f'only from {shop}'}, json_dumps_params={'ensure_ascii': False})

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
        serializer_order = OrderSerializer(order, data=request.data, partial=True)
        if serializer_order.is_valid():
            serializer_order.save()
        return JsonResponse({f'order with id {order.id}': 'was patched successfully'})

    def delete(self, request):
        answer = validate_and_get_user(request.headers)
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.is_superuser:
            orders = Order.objects.filter(state='canceled').delete()
            return JsonResponse({'orders with state canceled': 'were deleted'})
        orders = Order.objects.filter(state='canceled', user=user.id).delete()
        return JsonResponse({'your orders with state canceled': 'were deleted'})


class NewOrdersView(APIView):

    def get(self, request):
        answer = validate_and_get_user(request.headers)
        result = []
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'shop':
            return JsonResponse({'this function': 'only for shops'})
        for s in user.shops.all():
            orders = Order.objects.filter(state='new', shop=s)
            result_items = []
            for order in orders:
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
                result.append({ 'shop': str(s), str(order): result_items})
        return JsonResponse({'NEW orders': result}, json_dumps_params={'ensure_ascii': False})

    def post(self, request):
        answer = validate_and_get_user(request.headers)
        result = []
        if type(answer) is str:
            return JsonResponse({answer: 'check data'})
        user = list(answer.keys())[0]
        if user.type != 'shop':
            return JsonResponse({'this function': 'only for shops'})
        order_id = request.data['order_id']
        contact_id = request.data['contact_id']
        order = Order.objects.filter(id=order_id, state='new')
        if not order:
            return JsonResponse({'this order': 'does not exist'})











