from unittest import TestCase

from pabutools.election import OrdinalBallot, ApprovalBallot
from pabutools.election.pabulib import (
    parse_pabulib,
    parse_pabulib_from_string,
    parse_pabulib_from_url,
    write_pabulib,
    election_as_pabulib_string,
)

import os

from tests.test_class_inheritence import check_members_equality


class TestPabulib(TestCase):
    def test_approval(self):
        contents = """META
key;value
description;Local PB in Warsaw, WesoÅ‚a | Plac Wojska Polskiego
country;Poland
unit;Warszawa
subunit;Plac Wojska Polskiego
instance;2017
district;WesoÅ‚a
num_projects;4
num_votes;27
budget;51195
vote_type;approval
rule;greedy
date_begin;14.06.2016
date_end;24.06.2016
min_length;1
max_sum_cost;51195
language;polish
edition;3
PROJECTS
project_id;cost;category;votes;name;target;selected
427;15995;education;16;Akademia Szkraba;children,families with children;1
915;5825;education,environmental protection;14;Plac Wojska Polskiego dla gniazdujÄ…cych;None;1
2567;20000;education,sport,health;12;Aktywny senior - gimnastyka;seniors;1
1623;2900;public space,health;5;Å»yczliwoÅ›Ä‡ wobec kobiet w ciÄ…Å¼y dla mieszkanek WesoÅ‚ej.;adults,people with disabilities;1
VOTES
voter_id;age;sex;voting_method;vote
5642;33;F;internet;427
7230;65;F;internet;2567
8987;30;F;internet;915
10533;20;F;internet;915
15240;37;M;internet;427,915,2567,1623
16498;67;M;paper;2567,915
16910;68;F;paper;2567,915
22288;24;F;internet;427,2567,915
24842;14;M;internet;2567
32398;29;F;internet;915,1623,2567,427
32998;29;F;internet;427
44924;36;F;internet;427
47826;69;F;paper;2567,1623
48423;10;F;internet;915
48974;52;F;internet;427
50829;36;F;internet;427,2567,1623,915
57441;26;F;internet;915,2567,427
57475;64;M;internet;915,427
72881;33;F;internet;915
79157;52;F;internet;427
80175;38;F;internet;2567
87967;34;M;paper;427,2567,1623,915
88076;28;F;internet;427
88639;63;M;internet;915
94116;33;M;internet;427
103942;54;M;internet;427
104255;53;F;internet;427"""

        with open("test.pb", "w", encoding="utf-8") as f:
            f.write(contents)

        for instance, profile in [
            parse_pabulib("test.pb"),
            parse_pabulib_from_string(contents),
        ]:
            assert len(instance) == 4
            assert instance.budget_limit == 51195
            assert len(profile) == 27
            assert len(profile[0]) == 1
            assert len(profile[4]) == 4
            for p in profile[0]:
                assert p.name == "427"
                assert p.cost == 15995
            assert profile.approval_score(instance.get_project("427")) == 16
            assert len(profile.approved_projects()) == 4
            assert len(instance.categories) == 5
            assert len(instance.targets) == 5

        os.remove("test.pb")

    def test_empty_voters(self):
        contents = """META
key;value
description;Auto-filled description
country;Auto-filled country
unit;Auto-filled unit
instance;Auto-filled instance
num_projects;20
num_votes;1000
budget;600000
vote_type;approval
rule;Auto-filled rule
PROJECTS
project_id;cost
p0;124200
p1;128400
p2;135600
p3;128400
p4;316929
p5;51599
p6;66000
p7;55200
p8;55800
p9;54000
p10;66600
p11;61199
p12;51000
p13;59400
p14;59400
p15;58800
p16;63000
p17;64800
p18;66000
p19;57600
VOTES
voter_id;vote
0;p12,p19,p1,p14
1;p11,p1,p13
2;p16
3;p12,p4,p9
4;p0
5;p12,p18,p16,p2
6;
7;p6,p3,p13,p17,p19
8;p5,p10
9;
10;p0,p2
11;p11,p6,p2
12;p16,p19
13;
14;p10,p2"""

        with open("test.pb", "w", encoding="utf-8") as f:
            f.write(contents)

        for instance, profile in [
            parse_pabulib("test.pb"),
            parse_pabulib_from_string(contents),
        ]:
            assert len(instance) == 20
            assert len(profile) == 15
            assert profile[6] == ApprovalBallot()

        os.remove("test.pb")

    def test_cumulative(self):
        contents = """META
key;value
description;Municipal PB in Toulouse
country;France
unit;Toulouse
instance;2019
num_projects;30
num_votes;1494
budget;1000000
vote_type;cumulative
rule;greedy
date_begin;11.09.2019
date_end;15.10.2019
max_points;3
max_sum_points;7
language;french
edition;1
PROJECTS
project_id;cost;public_id;proposer;subunit;name;votes
1;7000;12;Julie 21;ARENES;Compostons ensemble !;215
2;35000;25;Conseil Citoyen;BELLEFONTAINE MILAN;Panneau d'affichage électronique extérieur;26
3;50000;19;Felix;ARENES;Eclairage public d’un chemin piéton-vélo rue Ella Maillart;92
4;390000;23;Perrine;PRADETTES;Tous à la Ramée à vélo ! A pied, en trottinette et rollers !;471
5;168000;1;Les usagers du parc;NEGRENEYS;Le parc des Anges vu par ses usagers;205
6;5000;10;Raymonde RENAUD;EMPALOT;Grillades et chaises longues;92
7;20000;5;A/KARIM;EMPALOT;Agir pour le sport Bien être ensemble à Empalot;99
8;110000;29;Conseil Citoyen;MILAN;Embellissement et aménagement d’un chemin piétonnier;45
9;270000;15;MOI;CEPIERES BEAUREGARD;Toilettes Publiques Jardin du Barry;65
10;2000;8;FonkDave;TROIS COCUS LA VACHE;Halte aux moustiques !;287
11;110000;22;Association Holons de Garonne;BELLEFONTAINE;Traversée : sculpture pour le bassin de Candilis (avec l'étanchéification du bassin);88
12;4000;20;Yamina;BAFAPATABOR;Cultivons la solidarité !;59
13;107000;2;Association Jardin Partagé;MARAICHERS;Un jardin urbain innovant pour mieux vivre ensemble au coeur des Maraîchers.  Jardinons, innovons, protégeons, partageons !;305
14;5000;27;Gilles Couralet;BELLEFONTAINE MILAN;Securisation de la route de Seysses;55
15;164000;4;Jardivert;TROIS COCUS LA VACHE;Création du jardin partagé des 3 Cocus;161
16;45000;28;Ahlam et Kafine;MIRAIL UNIVERSITE;Parc enfant sécurisé pour moins de 3 ans;332
17;29000;14;(R.E.R.S) Réseau d'Echanges Réciproques et de Savoirs;BAGATELLE;Complément d'équipement du parc de la Gironde;31
18;15000;24;Flo et Marie-Hélène;PRADETTES;Parcours de Santé à Viollet le duc;142
19;160000;7;Habitants et Associations Solidaires Unis pour Réussir Empalot HASURE;EMPALOT;Une halle couverte;55
20;2000;13;COPROPRIETE HIPPODROME;CEPIERE BEAUREGARD;Nichoirs pour mésanges;278
21;85000;17;Nielda;BAGATELLE FAOURETTE;Sécurité durable autour du Tunnel Vestrepain;69
22;241000;3;Les habitants de Negreneys;NEGRENEYS;projet d'aménagement des jardins de Negreneys;120
23;35000;26;Centre Social Bellefontaine;BELLEFONTAINE;Embellir et protéger les abords du jardin du Tintoret;44
24;10000;30;Mairie de Toulouse;REYNERIE;Panneau d’affichage pour les infos du quartier;34
25;44000;6;Convivialité Gloire Soupetard;SOUPETARD;Aire de convivialité et de jeux;90
26;25000;9;Conseil Citoyen Soupetard-La Gloire;SOUPETARD;Espace inter associatif / Maison des projets et services;58
27;10000;18;Comité de l'Ecoquartier Cartoucherie;CEPIERE BEAUREGARD;Panneau d'affichage pour les informations du quartier;68
28;100000;11;Comité de l'Ecocartoucherie;CEPIERE BEAUREGARD;Equipement sportifs pour enfants et adolescents;163
29;199000;21;Christian Moretto + Richard SL + Malik Beldjoudi;PRADETTES;Des jardins aux Pradettes;234
30;5000;16;Association 2Pieds 2Roues;BAFAPATABOR;Stations vélos : atelier de réparation et de gonflage;269
VOTES
voter_id;vote;points
0;10,11,13,9;2,2,2,1
1;6,25,5,22;3,2,1,1
2;22,3,20;3,2,2
3;14,23,2;3,3,1
4;5,10,11,13,20;3,1,1,1,1
5;1,25,5,7,29;2,2,1,1,1
6;5,10,13,20,30;3,1,1,1,1
7;6,7;3,3
8;14,8,2,4;3,2,1,1
9;1,6,7,9,10,20,30;1,1,1,1,1,1,1
10;6,7;3,3
11;2,14,8;3,3,1
12;
13;6,7;3,3"""

        with open("test.pb", "w", encoding="utf-8") as f:
            f.write(contents)

        for instance, profile in [
            parse_pabulib("test.pb"),
            parse_pabulib_from_string(contents),
        ]:
            assert len(instance) == 30
            assert instance.budget_limit == 1000000
            assert len(profile) == 14
            assert len(profile[0]) == 4
            assert len(profile[4]) == 5

            projects = {i: instance.get_project(str(i)) for i in range(1, 31)}
            assert profile[0][projects[9]] == 1
            assert profile[0][projects[10]] == 2
            assert profile[0][projects[11]] == 2
            assert profile[0][projects[13]] == 2
            assert profile[4][projects[5]] == 3
            assert profile[4][projects[10]] == 1
            assert profile[4][projects[11]] == 1
            assert profile[4][projects[13]] == 1
            assert profile[4][projects[20]] == 1
            assert len(instance.categories) == 0
            assert len(instance.targets) == 0

        os.remove("test.pb")

    def test_scoring(self):
        contents = """META
key;value
description;Municipal PB in Toulouse
country;France
unit;Toulouse
instance;2019
num_projects;30
num_votes;1494
budget;1000000
vote_type;scoring
rule;greedy
date_begin;11.09.2019
date_end;15.10.2019
language;french
edition;1
PROJECTS
project_id;cost;public_id;proposer;subunit;name;votes
1;7000;12;Julie 21;ARENES;Compostons ensemble !;215
2;35000;25;Conseil Citoyen;BELLEFONTAINE MILAN;Panneau d'affichage électronique extérieur;26
3;50000;19;Felix;ARENES;Eclairage public d’un chemin piéton-vélo rue Ella Maillart;92
4;390000;23;Perrine;PRADETTES;Tous à la Ramée à vélo ! A pied, en trottinette et rollers !;471
5;168000;1;Les usagers du parc;NEGRENEYS;Le parc des Anges vu par ses usagers;205
6;5000;10;Raymonde RENAUD;EMPALOT;Grillades et chaises longues;92
7;20000;5;A/KARIM;EMPALOT;Agir pour le sport Bien être ensemble à Empalot;99
8;110000;29;Conseil Citoyen;MILAN;Embellissement et aménagement d’un chemin piétonnier;45
9;270000;15;MOI;CEPIERES BEAUREGARD;Toilettes Publiques Jardin du Barry;65
10;2000;8;FonkDave;TROIS COCUS LA VACHE;Halte aux moustiques !;287
11;110000;22;Association Holons de Garonne;BELLEFONTAINE;Traversée : sculpture pour le bassin de Candilis (avec l'étanchéification du bassin);88
12;4000;20;Yamina;BAFAPATABOR;Cultivons la solidarité !;59
13;107000;2;Association Jardin Partagé;MARAICHERS;Un jardin urbain innovant pour mieux vivre ensemble au coeur des Maraîchers.  Jardinons, innovons, protégeons, partageons !;305
14;5000;27;Gilles Couralet;BELLEFONTAINE MILAN;Securisation de la route de Seysses;55
15;164000;4;Jardivert;TROIS COCUS LA VACHE;Création du jardin partagé des 3 Cocus;161
16;45000;28;Ahlam et Kafine;MIRAIL UNIVERSITE;Parc enfant sécurisé pour moins de 3 ans;332
17;29000;14;(R.E.R.S) Réseau d'Echanges Réciproques et de Savoirs;BAGATELLE;Complément d'équipement du parc de la Gironde;31
18;15000;24;Flo et Marie-Hélène;PRADETTES;Parcours de Santé à Viollet le duc;142
19;160000;7;Habitants et Associations Solidaires Unis pour Réussir Empalot HASURE;EMPALOT;Une halle couverte;55
20;2000;13;COPROPRIETE HIPPODROME;CEPIERE BEAUREGARD;Nichoirs pour mésanges;278
21;85000;17;Nielda;BAGATELLE FAOURETTE;Sécurité durable autour du Tunnel Vestrepain;69
22;241000;3;Les habitants de Negreneys;NEGRENEYS;projet d'aménagement des jardins de Negreneys;120
23;35000;26;Centre Social Bellefontaine;BELLEFONTAINE;Embellir et protéger les abords du jardin du Tintoret;44
24;10000;30;Mairie de Toulouse;REYNERIE;Panneau d’affichage pour les infos du quartier;34
25;44000;6;Convivialité Gloire Soupetard;SOUPETARD;Aire de convivialité et de jeux;90
26;25000;9;Conseil Citoyen Soupetard-La Gloire;SOUPETARD;Espace inter associatif / Maison des projets et services;58
27;10000;18;Comité de l'Ecoquartier Cartoucherie;CEPIERE BEAUREGARD;Panneau d'affichage pour les informations du quartier;68
28;100000;11;Comité de l'Ecocartoucherie;CEPIERE BEAUREGARD;Equipement sportifs pour enfants et adolescents;163
29;199000;21;Christian Moretto + Richard SL + Malik Beldjoudi;PRADETTES;Des jardins aux Pradettes;234
30;5000;16;Association 2Pieds 2Roues;BAFAPATABOR;Stations vélos : atelier de réparation et de gonflage;269
VOTES
voter_id;vote;points
0;10,11,13,9;2,2,2,1
1;6,25,5,22;3,2,1,1
2;22,3,20;3,2,2
3;14,23,2;3,3,1
4;5,10,11,13,20;3,1,1,1,1
5;1,25,5,7,29;2,2,1,1,1
6;5,10,13,20,30;3,1,1,1,1
7;6,7;3,3
8;14,8,2,4;3,2,1,1
9;1,6,7,9,10,20,30;1,1,1,1,1,1,1
10;6,7;3,3
11;2,14,8;3,3,1
12;"""

        with open("test.pb", "w", encoding="utf-8") as f:
            f.write(contents)

        for instance, profile in [
            parse_pabulib("test.pb"),
            parse_pabulib_from_string(contents),
        ]:
            assert profile[0][instance.get_project("10")] == 2
            assert profile[0][instance.get_project("9")] == 1
            assert profile[11][instance.get_project("8")] == 1

        os.remove("test.pb")

    def test_ordinal(self):
        contents = """META
key;value
description;Municipal PB in Kraków
country;Poland
unit;Kraków
instance;2018
num_projects;123
num_votes;32958
budget;8000100
vote_type;ordinal
rule;greedy
date_begin;16.06.2018
date_end;30.06.2018
min_length;3
max_length;3
language;polish
edition;5
PROJECTS
project_id;cost;votes;score;name
23;1725000;6512;14142;Zielony pochłaniacz smogu dla każdej dzielnicy!
26;1700000;3780;8153;Tężnia solankowa
18;2400030;2817;6068;CZYŻBY ZAPOMNIANO O ZALEWIE NOWOHUCKIM... i NOWEJ HUCIE ?
120;296310;2687;5762;Bezpieczny ratownik - Bezpieczny Krakowianin
95;1500000;2574;5069;Kąpielisko nad Bagrami Wielkimi - plaża i toalety
34;2400000;2167;5033;ZIELONA KRUPNICZA, CZYLI ULICA PRZYJAZNA DLA MIESZKAŃCÓW
39;700000;1998;4561;Winda dla chorych
51;420000;2082;4503;Młynówka Królewska - tworzymy najdłuższy park w Polsce
27;2275000;2029;4296;TAK DLA WILGI
7;860000;2416;4185;Donice zamiast słupków.
8;40700;2086;4019;Łączymy Parki Krakowa
3;645000;1781;3617;REWITALIZACJA ALEI SŁOWACKIEGO
123;260000;2008;3570;Ekologicznie przeciw komarom!
62;2400000;1867;3438;Kocham Staw Płaszowski
97;300000;1247;3267;Czerwone korale - magia stroju krakowskiego
80;299999;1768;3239;NOWOCZESNY AMBULANS MEDYCZNY
4;2320000;1501;3168;REWITALIZACJA PARKU KLEPARSKIEGO
36;2400020;1607;3154;Nowy Park w Krakowie
58;2400000;1563;3125;REWITALIZACJA PARKU MŁYNÓWKA KRÓLEWSKA ŁĄCZY DZIELNICE 1,5,6
92;740000;1344;2663;Rowerem i pieszo bezpiecznie z mostu Wandy
22;258000;966;2488;Przystanek początkowy 164 na pętli Piaski Nowe
60;1000000;1239;2462;MAGICZNY PLAC ZABAW W PARKU JORDANA (K.DOMU HARCERZA)
9;200000;1289;2397;Ogród witalny ... mimo że szpitalny! 
103;550000;1121;2347;PLAC AKTYWNEGO WYPOCZYNKU DLA MŁODZIEŻY NA ZAKRZÓWKU
19;1500000;1118;2337;Magiczny Park Kozłówek
89;504300;1157;2284;Budowa ciągu pieszo-rowerowego wzdłuż al.Bora Komorowskiego
35;800000;1188;2283;#BezpieczniNaBulwarach
56;2400030;959;2269;DOŚĆ DZIUR - WsPóLnIe WYREMONTUJMY Bieńczycką i Kocmyrzowską
78;170000;1356;2251;Dęby zamiast pomników
15;250000;1162;2163;BON KULTURALNY DLA SENIORA
83;1800000;1146;2102;Zielone Aleje Miejskie
67;150000;1027;2079;SMOK CO KROK czyli szlakiem krakowskich smoków 
122;1539520;1066;2055;Ścieżka rowerowa od ul. Rydla do ul. Wrocławskiej
53;55000;1063;1991;Biblioteka Gier Planszowych
52;150000;908;1930;Zaczytaj się w Krakowie
117;25000;1498;1895;Mali Ratownicy 
90;2400000;970;1845;Zielona Twierdza 
6;134050;974;1835;Rowerem z Krupniczej na Ingardena
81;1440000;971;1756;Bezpieczny Kraków dzięki monitoringowi
1;1500000;699;1747;Spraw aby samolot przy ważnej trasie odzyskał piękno.
17;35600;903;1702;Trening samoobrony i asertywności dla dziewcząt
76;1050000;853;1691;Aleja Róż na nowo – cz. 2: mała architektura
42;2400000;867;1660;"Z rozkładem autobusów ""za pan brat"" "
70;2400030;916;1649;Renowacja, oznakowanie i promocja  KOPCA WANDY
91;1740000;646;1635;Bezpieczny chodnik do Tyńca
12;210000;862;1554;(NIE) POŁAMCIE SOBIE NÓG!
5;32750;803;1509;Senior z pasją
106;68500;808;1387;Zielona Aleja Konopnickiej
61;185000;885;1381;70 dobrych uczynków na 70 lat Nowej Huty
63;350000;736;1372;Plac Zabaw dla Dorosłych
72;1500000;575;1318;ORLIK POD BALONEM
101;250000;629;1306;ul. Bonarka z miejscem odpoczynku mieszkańców
112;183900;605;1278;Asystent Osoby Niepełnosprawnej
44;1500000;656;1263;Park aktywności i rekreacji ze strefą dla czworonogów
87;1100000;548;1226;W malinowym chruśniaku!- krakowski ogród społecznościowy
65;600000;526;1222;Sygnalizacja świetlna:  Malborska - Macedońska - Szkolna
55;900000;647;1189;Nowe miejsca relaksu przy zdrojach artezyjskich
10;137800;553;1103;Program profilaktyczny o zdrowym odżywianiu dla przedszkoli
48;134000;524;1086;Na rolkach do pracy - połączenie dzielnic śródmiejskich
116;21000;465;1084;Modernizacja trasy biegowej parkrun w Krakowie.
11;300000;627;1083;Elektroniczne tablice informacyjne przy głównych arteriach
114;195000;528;1061;przystańMAM! - stworzenie miejsc dla osób z małymi dziećmi
45;400000;532;980;Asocjacja Promotorów Radosnego Ptaka - szlaki ornitologiczne
64;31000;546;970;Kultura w zasięgu ręku seniora
115;1000000;508;953;NOWY PLAC ZABAW NA PLANTACH PRZY DWORCU GŁÓWNYM
85;1780000;470;948;Mobilne kapsuły inhalacyjne2019-nowa jakość zdrowego oddechu
107;2400000;352;943;Poprawa bezpieczeństwa na ul.Rącznej
69;2400000;468;909;Które Rondo Mogilskie?
121;844000;437;899;Parking dla mieszkańców i pacjentów przychodni - Kozłówek
41;50000;507;877;Drzewa dla Cmentarza Rakowickiego
33;238500;423;840;Centrum Mechatroniki i Robotyki
68;720000;395;826;Budowa boiska wielofunkcyjnego w sercu Czyżyńskich osiedli
94;451000;438;807;Miejski Relaks
66;318560;306;789;STUDENT Z WERWĄ - bezpłatne zajęcia dla studentów
84;192000;446;766;Zazieleńmy Bulwar Wołyński!
50;1000000;344;739;Park rozrywki na Chełmie
102;576000;417;729;Samoobsługowy Kraków
75;2270000;385;724;Strzelanie - bawi i uczy
111;650000;367;721;Plac zabaw na Kurdwanowie - bezpiecznie i kreatywnie
47;369800;424;710;SMOK vs SMOG - THERMOS CUBE 59 solarna altanka maluszka
2;140000;332;677;"Cykl zawodów biegowych ""Moja przygoda z bieganiem"" "
86;46000;384;675;Spływ kajakowy po Rudawie – nowa atrakcja dla krakowian
99;2400000;350;639;Zaparkuj w Podgórzu
29;180000;352;626;Siłownia pod chmurką przy Kopcu Kosciuszki
109;482360;326;623;Roztańczony Kraków
105;220000;299;620;Bieńczycki Psi Wybieg
88;120000;313;579;Remont chodnika w ul.Kobierzyńskiej
79;150000;287;577;LEKKI TORNISTER = ZDROWE DZIECKO
46;619300;293;564;Stop utonięciom!- Bezpiecznie nad wodą w Krakowie.
43;550000;253;555;Bezpiecznie do Lidla, (nie) połamcie sobie nóg!
74;199200;310;545;Zdrowy Kraków - siła kobiet!
13;1500000;291;537;Poskaczmy razem !!! - kolejne TRAMPOLINY w Bieńczycach
59;46000;213;504;Szkolenie żeglarskie kadr drużyn żeglarskich w Krakowie
82;1000000;237;472;Odnowa i zagospodarowanie parku przy ul. Tomickiego
38;25000;281;471;Dzieci tkwiące tylko w sieci, mają w głowie same śmieci
104;140300;237;467;Budowa ogólnodostępnego placu zabaw przy ul. Cechowej 57
21;88500;247;443;Akademia Decjusza
110;800000;284;407;Młynówka Królewska i Stara Krowodrza - Trasa Historyczna
30;25000;244;404;Kino dla Seniora - 2500 darmowych biletów do Kina Paradox
108;1400000;201;382;Budowa brodzika dla dzieci na basenie Wandzianka
20;60000;212;375;Solarny kącik wypoczynku w ogrodzie przy Krupniczej 38
16;25000;196;353;„Pełnia życia, pełnia sił”
71;125000;186;316; Kopiec Kościuszki - Pomnikiem Historii
98;25200;174;302;Duzi Ratownicy
73;58000;161;301;Święto Cykliczne 2019
119;53300;132;271;Teatr Rodz-INNY
54;40220;143;258;Super Rodzic
77;905000;131;255;Doświetlamy Planty Bieńczyckie
93;100000;130;243;Zaczarowana scena w ogrodzie przy Krupniczej 38
14;2260000;115;224;POMOŻECIE ... ? Przebudujmy WSPÓLNIE ul. Wojciechowskiego
25;78000;93;186;Dzień z pasją motywacją  samodyscypliną-warsztaty dla dzieci
96;190000;109;183;Kochasz swój kraj to po nim nie bazgraj - kampania społeczna
28;35500;81;166;Spotkania ze sztuką cyrkową, aktywny kraków
118;147600;78;156;Klimatyzacja dla klubu Jędruś na os. Centrum A
100;165500;82;152;Hutniczek Robotniczek czyli Szlakiem Odkrywców Nowej Huty
40;75600;83;149;Warsztaty wprowadzające w świat nowoczesnej elektroniki
32;120000;77;121;Rewitalizacja zieleni przy budynku os. Sportowe 24 Kraków
24;76000;62;116;"I INTEGRACYJNE ZAWODY PŁYWACKIE ""FAMILY RACE – KRAKÓW 2019"" "
49;65000;61;101;KRK nasz Kraków. Miejsce spotkań
113;46800;63;96;Cały ten zgiełk
31;298000;54;94;"Uwertura koncertowa ""Cracovia"" "
37;28000;53;83;" ""Co nas uszczęśliwia w Krakowie"" - Konkurs fotograficzny"
57;25000;26;43;Krakowskie hulanie na gościńcu i wyścig na 1 kilometr
VOTES
voter_id;vote;voting_method;district
0;34,74,23;paper;PODGÓRZE DUCHACKIE
1;20,34,17;internet;GRZEGÓRZKI
2;17,23,11;internet;NOWA HUTA
3;18,3,34;internet;CZYŻYNY
4;97,120,117;paper;NOWA HUTA
5;22,19,95;internet;PODGÓRZE DUCHACKIE
6;19,7,26;internet;BIEŻANÓW-PROKOCIM
7;3,34,83;internet;CZYŻYNY
8;23,48,74;paper;ZWIERZYNIEC
9;43,61,56;paper;WZGÓRZA KRZESŁAWICKIE
10;56,39,12;internet;CZYŻYNY
11;67,94,49;internet;KROWODRZA
12;8,16,13;internet;BIEŻANÓW-PROKOCIM
13;23,86,102;internet;NOWA HUTA
14;63,83,23;paper;PODGÓRZE
15;120,87,106;paper;DĘBNIKI
16;9,23,70;internet;NOWA HUTA
17;120,87,106;paper;DĘBNIKI
18;18,4,55;internet;PRĄDNIK BIAŁY
19;39,9,23;paper;MISTRZEJOWICE
20;69,103,23;internet;DĘBNIKI
21;60,72,66;paper;ZWIERZYNIEC
22;97,120,117;paper;NOWA HUTA
23;56,18,61;paper;WZGÓRZA KRZESŁAWICKIE
24;42,29,36;internet;ZWIERZYNIEC
25;80,39,10;paper;BIEŻANÓW-PROKOCIM
26;119,23,33;internet;PODGÓRZE DUCHACKIE
27;120,72,26;internet;PODGÓRZE
28;33,121,104;internet;SWOSZOWICE
29;6,75,13;paper;BRONOWICE
30;78,4,5;internet;STARE MIASTO
31;29,36,41;internet;ZWIERZYNIEC
32;23,123,102;internet;ŁAGIEWNIKI-BOREK FAŁĘCKI
33;103,106,83;internet;DĘBNIKI
34;3,7,10;paper;PRĄDNIK CZERWONY
35;83,61,75;internet;PRĄDNIK CZERWONY
36;4,41,21;internet;STARE MIASTO
37;7,23,115;paper;STARE MIASTO
38;34,42,78;internet;PODGÓRZE
39;103,17,119;internet;STARE MIASTO
40;2,4,10;internet;WZGÓRZA KRZESŁAWICKIE
41;121,19,95;internet;BIEŻANÓW-PROKOCIM
42;95,75,111;paper;PODGÓRZE DUCHACKIE
43;84,101,83;internet;PODGÓRZE
44;4,36,41;internet;KROWODRZA
45;;internet;KROWODRZA
"""

        with open("test.pb", "w", encoding="utf-8") as f:
            f.write(contents)

        for instance, profile in [
            parse_pabulib("test.pb"),
            parse_pabulib_from_string(contents),
        ]:
            assert len(instance) == 123
            assert instance.budget_limit == 8000100
            assert len(profile) == 46
            assert len(profile[44]) == 3
            assert len(profile[4]) == 3

            assert profile[44] == OrdinalBallot(
                [
                    instance.get_project("4"),
                    instance.get_project("36"),
                    instance.get_project("41"),
                ]
            )

        os.remove("test.pb")

    def test_wrong_type(self):
        contents = """META
                key;value
                description;Municipal PB in Kraków
                country;Poland
                unit;Kraków
                instance;2018
                num_projects;123
                num_votes;32958
                budget;8000100
                vote_type;SQKJHGLUHDFVJHFVIEUDFKEF
                rule;greedy
                date_begin;16.06.2018
                date_end;30.06.2018
                min_length;3
                max_length;3
                language;polish
                edition;5
                PROJECTS
                project_id;cost;votes;score;name
                23;1725000;6512;14142;Zielony pochłaniacz smogu dla każdej dzielnicy!
                26;1700000;3780;8153;Tężnia solankowa
                18;2400030;2817;6068;CZYŻBY ZAPOMNIANO O ZALEWIE NOWOHUCKIM... i NOWEJ HUCIE ?
                120;296310;2687;5762;Bezpieczny ratownik - Bezpieczny Krakowianin
                95;1500000;2574;5069;Kąpielisko nad Bagrami Wielkimi - plaża i toalety
                34;2400000;2167;5033;ZIELONA KRUPNICZA, CZYLI ULICA PRZYJAZNA DLA MIESZKAŃCÓW
                VOTES
                voter_id;vote;voting_method;district
                0;34,74,23;paper;PODGÓRZE DUCHACKIE
                1;20,34,17;internet;GRZEGÓRZKI
                2;17,23,11;internet;NOWA HUTA
                3;18,3,34;internet;CZYŻYNY
                4;97,120,117;paper;NOWA HUTA
            """
        with open("test.pb", "w", encoding="utf-8") as f:
            f.write(contents)

        try:
            _, _ = parse_pabulib("test.pb")
        except NotImplementedError:
            pass
        finally:
            os.remove("test.pb")

    def test_legal_defaults(self):
        contents = """META
                key;value
                description;Municipal PB in Kraków
                country;Poland
                unit;Kraków
                instance;2018
                budget;8000100
                vote_type;approval
                min_length;1
                max_length;6
                min_sum_cost;0
                max_sum_cost;800010000
                min_sum_points;0
                max_sum_points;100
                min_points;0
                max_points;100
                PROJECTS
                project_id;cost;votes;score;name
                1;1725000;6512;14142;Zielony pochłaniacz smogu dla każdej dzielnicy!
                2;1700000;3780;8153;Tężnia solankowa
                3;2400030;2817;6068;CZYŻBY ZAPOMNIANO O ZALEWIE NOWOHUCKIM... i NOWEJ HUCIE ?
                VOTES
                voter_id;vote;voting_method;district
                0;1,2,3;paper;PODGÓRZE DUCHACKIE
            """
        with open("test.pb", "w", encoding="utf-8") as f:
            f.write(contents)
        instance, profile = parse_pabulib("test.pb")
        os.remove("test.pb")
        assert instance.meta["min_length"] == "1"
        assert instance.meta["max_length"] == "6"
        assert instance.meta["min_sum_cost"] == "0"
        assert instance.meta["max_sum_cost"] == "800010000"
        assert profile.legal_min_length is None
        assert profile.legal_max_length is None
        assert profile.legal_min_cost is None
        assert profile.legal_max_cost is None

        contents = """META
                key;value
                description;Municipal PB in Kraków
                country;Poland
                unit;Kraków
                instance;2018
                budget;8000100
                vote_type;cumulative
                min_length;1
                max_length;6
                min_cost;0
                min_sum_points;0
                max_sum_points;100
                min_points;0
                max_points;100
                max_cost;800010000
                PROJECTS
                project_id;cost;votes;score;name
                1;1725000;6512;14142;Zielony pochłaniacz smogu dla każdej dzielnicy!
                2;1700000;3780;8153;Tężnia solankowa
                3;2400030;2817;6068;CZYŻBY ZAPOMNIANO O ZALEWIE NOWOHUCKIM... i NOWEJ HUCIE ?
                VOTES
                voter_id;vote;points
                0;1,2,3;1,2,3
            """
        with open("test.pb", "w", encoding="utf-8") as f:
            f.write(contents)
        instance, profile = parse_pabulib("test.pb")
        os.remove("test.pb")

        assert instance.meta["min_points"] == "0"
        assert instance.meta["max_points"] == "100"
        assert instance.meta["max_sum_points"] == "100"
        assert profile.legal_min_score is None
        assert profile.legal_max_score is None
        assert profile.legal_min_total_score is None
        assert profile.legal_max_total_score == 100

    def test_url_parse(self):
        url = (
            "http://pabulib.org/tiles/download/poland_warszawa_2018_pole-mokotowskie.pb"
        )
        url_inst, url_prof = parse_pabulib_from_url(url)
        assert url_inst.file_name == "poland_warszawa_2018_pole-mokotowskie.pb"
        assert url_inst.file_path == url

        with open("test.pb", "w", encoding="utf-8") as f:
            f.write(
                """META
key;value
description;Local PB in Warszawa, Ochota | Pole Mokotowskie
country;Poland
unit;Warszawa
district;Ochota
subunit;Pole Mokotowskie
instance;2018
num_projects;1
num_votes;8
budget;21064
vote_type;approval
rule;greedy
date_begin;14.06.2017
date_end;30.06.2017
min_length;1
max_sum_cost;21064
edition;4
language;pl
currency;PLN
fully_funded;1
PROJECTS
project_id;cost;votes;name;category;target;selected
658;21064;8;Dobre grzyby (mikoryza) dla drzew Pola Mokotowskiego;environmental protection,public space,urban greenery;seniors,families with children,animals;1
VOTES
voter_id;vote;age;sex;voting_method
30397;658;43;F;internet
39076;658;61;F;paper
56422;658;66;M;internet
67344;658;32;F;internet
83776;658;73;F;internet
89587;658;9;M;internet
95332;658;31;F;internet
102415;658;24;F;internet
"""
            )

        file_inst, file_prof = parse_pabulib("test.pb")
        os.remove("test.pb")

        assert file_inst == url_inst
        assert len(file_inst) == len(url_inst)
        assert file_prof == url_prof
        assert len(file_prof) == len(url_prof)
        url_inst.file_name = "test.pb"
        url_inst.file_path = "test.pb"
        check_members_equality(file_inst, url_inst)
        check_members_equality(file_prof, url_prof)

    def test_write(self):
        contents = """META
key;value
description;Local PB in Warsaw, WesoÅ‚a | Plac Wojska Polskiego
country;Poland
unit;Warszawa
subunit;Plac Wojska Polskiego
instance;2017
district;WesoÅ‚a
num_projects;4
num_votes;27
budget;51195
vote_type;approval
rule;greedy
date_begin;14.06.2016
date_end;24.06.2016
min_length;1
max_sum_cost;51195
language;polish
edition;3
PROJECTS
project_id;cost;category;votes;name;target;selected
427;15995;education;16;Akademia Szkraba;children,families with children;1
915;5825;education,environmental protection;14;Plac Wojska Polskiego dla gniazdujÄ…cych;None;1
2567;20000;education,sport,health;12;Aktywny senior - gimnastyka;seniors;1
1623;2900;public space,health;5;Å»yczliwoÅ›Ä‡ wobec kobiet w ciÄ…Å¼y dla mieszkanek WesoÅ‚ej.;adults,people with disabilities;1
VOTES
voter_id;age;sex;voting_method;vote
5642;33;F;internet;427
7230;65;F;internet;2567
8987;30;F;internet;915
10533;20;F;internet;915
15240;37;M;internet;427,915,2567,1623
16498;67;M;paper;2567,915
16910;68;F;paper;2567,915
22288;24;F;internet;427,2567,915
24842;14;M;internet;2567
32398;29;F;internet;915,1623,2567,427
32998;29;F;internet;427
44924;36;F;internet;427
47826;69;F;paper;2567,1623
48423;10;F;internet;915
48974;52;F;internet;427
50829;36;F;internet;427,2567,1623,915
57441;26;F;internet;915,2567,427
57475;64;M;internet;915,427
72881;33;F;internet;915
79157;52;F;internet;427
80175;38;F;internet;2567
87967;34;M;paper;427,2567,1623,915
88076;28;F;internet;427
88639;63;M;internet;915
94116;33;M;internet;427
103942;54;M;internet;427
104255;53;F;internet;427"""

        with open("test.pb", "w", encoding="utf-8") as f:
            f.write(contents)
        instance, profile = parse_pabulib("test.pb")
        write_pabulib(instance, profile, "test_out.pb")
        instance_out, profile_out = parse_pabulib("test_out.pb")
        instance_out.file_name = "test.pb"
        instance_out.file_path = "test.pb"
        check_members_equality(instance, instance_out)
        check_members_equality(profile, profile_out)
        os.remove("test.pb")
        os.remove("test_out.pb")
