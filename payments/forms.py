
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import Payment
from tenants.models import Tenant


class PaymentForm(forms.ModelForm):

    class Meta:
        model = Payment

        fields = [
            'tenant',
            'payment_type',
            'amount',
            'payment_date',
            'payment_method',
            'transaction_code',
            'status',
            'description',
        ]

        widgets = {
            'tenant': forms.Select(attrs={
                'class': 'form-control'
            }),

            'payment_type': forms.Select(attrs={
                'class': 'form-control'
            }),

            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount in KES',
                'min': '0.01',
                'step': '0.01'
            }),

            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),

            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            }),

            'transaction_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter M-Pesa transaction code'
            }),

            'status': forms.Select(attrs={
                'class': 'form-control'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional payment notes'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['tenant'].queryset = Tenant.objects.filter(
            is_active=True,
            tenant_user__is_active=True,
            tenant_user__is_active_account=True
        ).select_related(
            'tenant_user',
            'property'
        )

    def clean_amount(self):

        amount = self.cleaned_data.get('amount')

        if amount is None or amount <= Decimal('0.00'):
            raise ValidationError(
                'Payment amount must be greater than zero.'
            )

        return amount

    def clean(self):

        cleaned_data = super().clean()

        payment_method = cleaned_data.get('payment_method')
        transaction_code = cleaned_data.get('transaction_code')

        if payment_method == 'mpesa':

            if not transaction_code or not transaction_code.strip():

                self.add_error(
                    'transaction_code',
                    'M-Pesa transaction code is required.'
                )

            else:

                transaction_code = transaction_code.strip()

                duplicate = Payment.objects.filter(
                    payment_method='mpesa',
                    transaction_code__iexact=transaction_code
                )

                if self.instance.pk:
                    duplicate = duplicate.exclude(
                        pk=self.instance.pk
                    )

                if duplicate.exists():

                    self.add_error(
                        'transaction_code',
                        'This M-Pesa transaction code has already been recorded.'
                    )

                cleaned_data['transaction_code'] = transaction_code

        return cleaned_data
