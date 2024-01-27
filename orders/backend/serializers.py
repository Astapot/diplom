from rest_framework import serializers

from .models import MyUser, Product, ProductInfo, Contact, Order, OrderItem


#
#
class MyUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = MyUser
        fields = ('id', 'username', 'password', 'type', 'email')


class ContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contact
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ('id', 'user', 'state', 'contact', 'ordered_items')
        extra_kwargs = {
            'ordered_items': {
                'required': False
            }
        }

class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = '__all__'






    # def update(self, instance, validated_data):
    #     instance.password = validated_data.get('password', instance.password)
    #     instance.save()
    #     return instance

# class ProductInfoSerializer(serializers.ModelSerializer):
#
#     class Meta:
#         model = ProductInfo
#         fields = ()

# class ProductSerializer(serializers.ModelSerializer):
#
#     model = ProductInfoSerializer()
#
#     class Meta:
#         model = Product
#         fields = ('name', 'category', )

