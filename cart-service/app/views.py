from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
import requests


BOOK_SERVICE_URL = "http://book-service:8000"


class CartListCreate(APIView):
    def get(self, request):
        carts = Cart.objects.all()
        return Response(CartSerializer(carts, many=True).data)

    def post(self, request):
        customer_id = request.data.get('customer_id')
        if customer_id in [None, ""]:
            return Response({'customer_id': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        cart, created = Cart.objects.get_or_create(customer_id=customer_id)
        serializer = CartSerializer(cart)
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=code)


class CartByCustomer(APIView):
    def get(self, request, customer_id):
        cart = Cart.objects.filter(customer_id=customer_id).first()
        if not cart:
            return Response({'detail': 'Cart not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CartSerializer(cart).data)

    def post(self, request, customer_id):
        cart, created = Cart.objects.get_or_create(customer_id=customer_id)
        serializer = CartSerializer(cart)
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=code)


class CartDetail(APIView):
    def put(self, request, cart_id):
        cart = get_object_or_404(Cart, pk=cart_id)
        serializer = CartSerializer(cart, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, cart_id):
        cart = get_object_or_404(Cart, pk=cart_id)
        cart.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemList(APIView):
    def get(self, request, cart_id):
        cart = get_object_or_404(Cart, pk=cart_id)
        items = CartItem.objects.filter(cart=cart)
        return Response(CartItemSerializer(items, many=True).data)


class AddCartItem(APIView):
    def post(self, request):
        cart_id = request.data.get('cart')
        book_id = request.data.get('book_id')
        try:
            quantity = int(request.data.get('quantity', 0) or 0)
        except (TypeError, ValueError):
            return Response({'quantity': 'Quantity must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        if not cart_id:
            return Response({'cart': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not book_id:
            return Response({'book_id': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if quantity <= 0:
            return Response({'quantity': 'Quantity must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)

        cart = Cart.objects.filter(pk=cart_id).first()
        if not cart:
            return Response({'detail': 'Cart does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        book_resp = requests.get(f"{BOOK_SERVICE_URL}/books/{book_id}/", timeout=5)
        if book_resp.status_code != 200:
            return Response({'detail': 'Book does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        existing_item = CartItem.objects.filter(cart=cart, book_id=book_id).first()
        if existing_item:
            existing_item.quantity += quantity
            existing_item.save(update_fields=['quantity'])
            return Response(CartItemSerializer(existing_item).data, status=status.HTTP_200_OK)

        serializer = CartItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartItemDetail(APIView):
    def get(self, request, item_id):
        item = get_object_or_404(CartItem, pk=item_id)
        return Response(CartItemSerializer(item).data)

    def put(self, request, item_id):
        item = get_object_or_404(CartItem, pk=item_id)

        quantity = request.data.get('quantity')
        if quantity is not None:
            try:
                quantity_value = int(quantity)
            except (TypeError, ValueError):
                return Response({'quantity': 'Quantity must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
            if quantity_value <= 0:
                return Response({'quantity': 'Quantity must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CartItemSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, item_id):
        item = get_object_or_404(CartItem, pk=item_id)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
