from django.shortcuts import render, redirect
from .models import Product ,Cart
from django.http import JsonResponse, HttpResponse
import json
from django.contrib import messages 
from django.shortcuts import get_object_or_404
import logging
import zipfile
import os
from django.conf import settings
from io import BytesIO


logger = logging.getLogger(__name__)

def view_product(request):
    context = {}
    products = Product.objects.all()
    
    # فیلتر بر اساس size (اگر در query string باشد)
    size_filter = request.GET.get('size')
    if size_filter:
        products = products.filter(size__icontains=size_filter)
    
    context['products'] = products
    return render(request, 'aminicar/main/index.html', context)



 
def product_detail(request, product_id):
    context = {}
    product = get_object_or_404(Product, id=product_id)
    
    context['product'] = product
    # size به صورت خودکار از product در دسترس است

    return render(request, 'aminicar/main/show_product.html', context)

def add_to_cart(request):
    
    current_user = request.user
    if request.method == "POST":
        if request.user.is_authenticated:
            product_id = int(request.POST.get('product_id'))
            print('Product ID:', product_id)
            # منطق اضافه کردن محصول به سبد خرید

            try:
                product_check = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                messages.error(request, 'No product was found with this identifier. Please try again.')
                return JsonResponse({'status': 'No such Product found'})

            if product_check:
                if Cart.objects.filter(user=current_user, product_id=product_id):
                    messages.warning(request, 'This product has already been added to your basket.')
                    return JsonResponse({'status': 'Product is Already in Cart'})
                else:
                    product_qyt = 1
                    Cart.objects.create(user=current_user, product_id=product_id, quantity=product_qyt)
                    messages.success(request, 'The product has been successfully added to your basket.')
                    return JsonResponse({'status': 'Product added successfully'})

        else:
            messages.error(request, 'Please sign in to your account first.')
            return JsonResponse({'status': 'Login to continue'})

    messages.error(request, 'Invalid request. Please try again.')
    return JsonResponse({'status': 'Invalid request'}, status=400)




def checkout(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Please sign in to your account first.')
        return redirect('login')  # یا صفحه‌ای که کاربر را به ورود هدایت کند

    context = {}
    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items.exists():
        messages.warning(request, 'Your basket is empty. Please add a product to your basket.')
        return redirect('cart')  # یا هر صفحه‌ای که محصولات را نمایش می‌دهد

    context['cart_items'] = cart_items
    context['cart_total'] = cart_items.count()
    cart_total=0
    total_price = 0
    for item in cart_items:
        total_price += item.product.price * item.quantity  # جمع کل قیمت محصولات با تعداد
        cart_total +=item.quantity
    context['total_price'] = total_price
    context['cart_total'] = cart_total

    messages.info(request, 'Please review your payment details.')

    return render(request, 'aminicar/main/checkout.html', context)





def update_cart(request):
    try:
        data = json.loads(request.body)
        prod_id = data.get('productId')
        action = data.get('action')
        logger.info(f"Product ID: {prod_id}, Action: {action}")

        cart_item = Cart.objects.get(user=request.user, product_id=prod_id)
        if action == 'add':
            cart_item.quantity += 1
        elif action == 'remove':
            cart_item.quantity -= 1
        logger.info(f"Quantity after update: {cart_item.quantity}")
        cart_item.save()

        if cart_item.quantity == 0:
            cart_item.delete()
            logger.info(f"Cart item deleted: {prod_id}")
        return JsonResponse({'status': "Update Successfully"})
    except Cart.DoesNotExist:
        logger.error(f"Cart item not found for Product ID: {prod_id}")
        return JsonResponse({'status': "Product not found in cart"}, status=404)
    except Exception as e:
        logger.error(f"Error updating cart: {e}")
        return JsonResponse({'status': "Error occurred"}, status=500)


def download_product_images(request, product_id):
    """دانلود تمام عکس‌های محصول به صورت ZIP"""
    product = get_object_or_404(Product, id=product_id)
    
    # ایجاد یک فایل ZIP در حافظه
    zip_buffer = BytesIO()
    added_files = set()  # برای جلوگیری از تکراری شدن فایل‌ها
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # لیست تمام فیلدهای عکس
        image_fields = ['image', 'image1', 'image2', 'image3', 'image4']
        
        for field_name in image_fields:
            image_field = getattr(product, field_name, None)
            if image_field and image_field.name:
                try:
                    # مسیر کامل فایل
                    image_path = os.path.join(settings.MEDIA_ROOT, image_field.name)
                    
                    # بررسی وجود فایل
                    if os.path.exists(image_path):
                        # نام فایل برای ZIP (با پیشوند برای جلوگیری از تکراری)
                        base_filename = os.path.basename(image_field.name)
                        # اگر فایل قبلاً اضافه شده، نام را تغییر می‌دهیم
                        if base_filename in added_files:
                            name, ext = os.path.splitext(base_filename)
                            filename = f"{name}_{field_name}{ext}"
                        else:
                            filename = base_filename
                        
                        zip_file.write(image_path, filename)
                        added_files.add(base_filename)
                except Exception as e:
                    logger.error(f"Error adding {field_name} to zip: {e}")
                    continue
    
    # بررسی اینکه آیا فایلی اضافه شده است
    if len(added_files) == 0:
        messages.error(request, 'هیچ عکسی برای دانلود موجود نیست.')
        return redirect('product:product_detail', product_id=product_id)
    
    # تنظیم response برای دانلود
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    # استفاده از slug برای نام فایل (امن‌تر از title)
    safe_filename = product.slug if hasattr(product, 'slug') else str(product.id)
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}_aminimart_product_images.zip"'
    
    return response


def download_current_image(request, product_id):
    """دانلود عکس فعلی که نمایش داده می‌شود"""
    product = get_object_or_404(Product, id=product_id)
    
    # دریافت index عکس از query parameter (0 برای image, 1 برای image1, و غیره)
    image_index = request.GET.get('index', '0')
    
    try:
        image_index = int(image_index)
    except ValueError:
        image_index = 0
    
    # لیست فیلدهای عکس
    image_fields = ['image', 'image1', 'image2', 'image3', 'image4']
    
    # بررسی محدوده معتبر
    if image_index < 0 or image_index >= len(image_fields):
        image_index = 0
    
    # دریافت فیلد عکس
    field_name = image_fields[image_index]
    image_field = getattr(product, field_name, None)
    
    if not image_field or not image_field.name:
        messages.error(request, 'عکس مورد نظر یافت نشد.')
        return redirect('product:product_detail', product_id=product_id)
    
    # مسیر کامل فایل
    image_path = os.path.join(settings.MEDIA_ROOT, image_field.name)
    
    if not os.path.exists(image_path):
        messages.error(request, 'فایل عکس یافت نشد.')
        return redirect('product:product_detail', product_id=product_id)
    
    # خواندن فایل و ارسال به عنوان response
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # تعیین نوع محتوا بر اساس پسوند فایل
    content_type = 'image/jpeg'  # پیش‌فرض
    if image_path.lower().endswith('.png'):
        content_type = 'image/png'
    elif image_path.lower().endswith('.gif'):
        content_type = 'image/gif'
    
    # نام فایل برای دانلود
    filename = os.path.basename(image_field.name)
    
    response = HttpResponse(image_data, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
