from linkextractor.utils import get_amount_cases_by_bwb_and_label_ids

law_list = [
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0002656",
        "bwb_label_id": 2750674,
        "title": "Burgerlijk Wetboek Boek 1, Artikel 1",
        "amount_related_cases": 23
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0002744",
        "bwb_label_id": 1205564,
        "title": "Besluit wettelijke rente, Artikel 1",
        "amount_related_cases": 12
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0002761",
        "bwb_label_id": 5000414,
        "title": "Burgerlijk Wetboek Boek 4, Artikel 1",
        "amount_related_cases": 27
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0003045",
        "bwb_label_id": 2867904,
        "title": "Burgerlijk Wetboek Boek 2, Artikel 1",
        "amount_related_cases": 110
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0005034",
        "bwb_label_id": 1763814,
        "title": "Burgerlijk Wetboek Boek 8, Artikel 1",
        "amount_related_cases": 49
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0005288",
        "bwb_label_id": 1723924,
        "title": "Burgerlijk Wetboek Boek 5, Artikel 1",
        "amount_related_cases": 340
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0005289",
        "bwb_label_id": 2905484,
        "title": "Burgerlijk Wetboek Boek 6, Artikel 1",
        "amount_related_cases": 54
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0005290",
        "bwb_label_id": 2911574,
        "title": "Burgerlijk Wetboek Boek 7, Artikel 1",
        "amount_related_cases": 184
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0005291",
        "bwb_label_id": 2898514,
        "title": "Burgerlijk Wetboek Boek 3, Artikel 1",
        "amount_related_cases": 145
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0006445",
        "bwb_label_id": 1990664,
        "title": "Besluit Werkloosheid onderwijs- en onderzoekpersoneel, Artikel 1",
        "amount_related_cases": 3
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0006950",
        "bwb_label_id": 1993564,
        "title": "Besluit woninggebonden subsidies 1995, Artikel 1",
        "amount_related_cases": 15
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0007523",
        "bwb_label_id": 1989064,
        "title": "Besluit uitvoering Wet arbeid vreemdelingen, Artikel 1",
        "amount_related_cases": 164
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0009934",
        "bwb_label_id": 898854,
        "title": "Besluit woon- en verblijfsgebouwen milieubeheer, Artikel 1",
        "amount_related_cases": 61
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0010000",
        "bwb_label_id": 942454,
        "title": "Besluit tegemoetkoming schade bij rampen en zware ongevallen, Artikel 1",
        "amount_related_cases": 8
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0012096",
        "bwb_label_id": 1417584,
        "title": "Besluit winstbepaling en reserves verzekeraars 2001, Artikel 1",
        "amount_related_cases": 21
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0012649",
        "bwb_label_id": 1541014,
        "title": "Besluit wegslepen van voertuigen, Artikel 1",
        "amount_related_cases": 52
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0028751",
        "bwb_label_id": 10946214,
        "title": "Burgerlijk Wetboek BES Boek 7, Artikel 1",
        "amount_related_cases": 1
    },
    {
        "type": "artikel",
        "number": "1",
        "bwb_id": "BWBR0030068",
        "bwb_label_id": 11316984,
        "title": "Burgerlijk Wetboek Boek 10, Artikel 1",
        "amount_related_cases": 13
    }
]

tuple_list = [(row['bwb_id'], row['bwb_label_id']) for row in law_list]

lookup_list = get_amount_cases_by_bwb_and_label_ids(tuple_list)

for law in law_list:
    law['check_related_cases'] = lookup_list.get((law['bwb_id'], law['bwb_label_id']))

print("the results of this test case will change in the future")

for law in law_list:
    assert law['check_related_cases'] == law['amount_related_cases'], "amount cases should be the same"
