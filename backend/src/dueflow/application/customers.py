from uuid import UUID

from dueflow.application.errors import ResourceNotFoundError
from dueflow.infrastructure.db.models import Customer
from dueflow.infrastructure.db.repositories import CustomerRepository


class CustomerService:
    def __init__(self, repository: CustomerRepository) -> None:
        self.repository = repository

    def create(self, *, name: str, phone: str, active: bool) -> Customer:
        customer = Customer(name=name, phone=phone, active=active)
        return self.repository.add(customer)

    def list(self, *, limit: int, offset: int) -> list[Customer]:
        return self.repository.list(limit=limit, offset=offset)

    def get(self, customer_id: UUID) -> Customer:
        customer = self.repository.get(customer_id)
        if customer is None:
            raise ResourceNotFoundError("cliente não encontrado")
        return customer

    def update(
        self,
        customer_id: UUID,
        *,
        name: str,
        phone: str,
        active: bool,
    ) -> Customer:
        customer = self.get(customer_id)
        customer.name = name
        customer.phone = phone
        customer.active = active
        return self.repository.save(customer)

