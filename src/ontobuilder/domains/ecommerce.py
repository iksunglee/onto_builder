"""E-commerce domain builder."""

from ontobuilder.core.ontology import Ontology
from ontobuilder.domains.base import DomainBuilder


class EcommerceDomainBuilder(DomainBuilder):
    @property
    def name(self) -> str:
        return "ecommerce"

    @property
    def description(self) -> str:
        return "Online retail and e-commerce domain"

    def build_template(self) -> Ontology:
        onto = Ontology("E-Commerce", description="E-commerce domain ontology")

        # Core concepts
        onto.add_concept("Product", description="An item available for sale")
        onto.add_concept("Category", description="A product category")
        onto.add_concept("Customer", description="A person who buys products")
        onto.add_concept("Order", description="A purchase order")
        onto.add_concept("Payment", description="A payment for an order")
        onto.add_concept("Review", description="A customer review of a product")

        # Product hierarchy
        onto.add_concept("PhysicalProduct", parent="Product", description="A tangible product")
        onto.add_concept("DigitalProduct", parent="Product", description="A downloadable product")

        # Properties
        onto.add_property("Product", "name", data_type="string", required=True)
        onto.add_property("Product", "price", data_type="float", required=True)
        onto.add_property("Product", "description", data_type="string")
        onto.add_property("Customer", "name", data_type="string", required=True)
        onto.add_property("Customer", "email", data_type="string", required=True)
        onto.add_property("Order", "date", data_type="date", required=True)
        onto.add_property("Order", "total", data_type="float")
        onto.add_property("Payment", "amount", data_type="float", required=True)
        onto.add_property("Payment", "method", data_type="string")
        onto.add_property("Review", "rating", data_type="int")
        onto.add_property("Review", "text", data_type="string")

        # Relations
        onto.add_relation("belongs_to", source="Product", target="Category")
        onto.add_relation("placed_by", source="Order", target="Customer")
        onto.add_relation("contains", source="Order", target="Product", cardinality="one-to-many")
        onto.add_relation("paid_with", source="Order", target="Payment")
        onto.add_relation("reviewed_by", source="Review", target="Customer")
        onto.add_relation("reviews", source="Review", target="Product")

        return onto

    def get_interview_hints(self) -> dict:
        return {
            "domain": "e-commerce",
            "description": self.description,
            "key_concepts": ["Product", "Customer", "Order", "Payment", "Category"],
            "common_relations": ["purchases", "belongs_to", "contains", "paid_with"],
        }

    def get_glossary(self) -> dict[str, str]:
        return {
            "SKU": "Stock Keeping Unit — a unique identifier for each product variant",
            "Cart": "A temporary collection of products a customer intends to buy",
            "Checkout": "The process of finalizing a purchase",
        }
