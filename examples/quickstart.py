"""Quick-start example: building a Pet Store ontology programmatically."""

from ontobuilder import Ontology

# Create an ontology
onto = Ontology("Pet Store", description="A pet store domain model")

# Add concepts
onto.add_concept("Animal", description="A living creature")
onto.add_concept("Dog", parent="Animal", description="A domestic dog")
onto.add_concept("Cat", parent="Animal", description="A domestic cat")
onto.add_concept("Store", description="A retail store")
onto.add_concept("Customer", description="A person who buys pets")

# Add properties
onto.add_property("Animal", "name", data_type="string", required=True)
onto.add_property("Animal", "age", data_type="int")
onto.add_property("Dog", "breed", data_type="string")
onto.add_property("Customer", "name", data_type="string", required=True)

# Add relations
onto.add_relation("sold_at", source="Animal", target="Store")
onto.add_relation("buys", source="Customer", target="Animal")

# Add instances
onto.add_instance("Rex", concept="Dog", properties={"name": "Rex", "breed": "Labrador"})
onto.add_instance("Whiskers", concept="Cat", properties={"name": "Whiskers", "age": 3})

# Display
print(onto.print_tree())
print()
print(onto)

# Save
from ontobuilder.serialization.yaml_io import save_yaml
save_yaml(onto, "pet_store.onto.yaml")
print("\nSaved to pet_store.onto.yaml")
