import json
import os

filepath = r'c:\Users\migue\Desktop\Bureau\DiscordLol\praises.json'

new_praises = {
    "Vex": [
        "Pff... victoire. Si tu veux.",
        "Ombre a fait tout le boulot.",
        "Tu as, reset l'ulti sur toute l'équipe.",
        "La déprime gagne toujours.",
        "Yordle gothique.",
        "Tu as fear tout le monde.",
        "Trop d'efforts... mais ça valait le coup.",
        "L'anti-dash ultime.",
        "Le monde est sombre, comme leur écran.",
        "Misère et victoire."
    ],
    "Vi": [
        "Vi, pour Violence !",
        "Tu as punché ton ticket pour la victoire.",
        "Gantelets Hextech chargés.",
        "L'ulti inarrêtable sur le carry.",
        "Piltover Enforcer.",
        "Tu as brisé leurs armures.",
        "Coup de poing dévastateur.",
        "J'aime quand ça craque.",
        "La loi, c'est mes poings.",
        "Tu as impacté la game."
    ],
    "Viego": [
        "Le Roi Déchu règne.",
        "Tu as possédé leurs âmes et leurs kits.",
        "Un champion ? Non, TOUS les champions.",
        "Le cœur brisé, mais le score entier.",
        "Brume noire envahissante.",
        "Lame du Roi Déchu.",
        "Reset en chaîne.",
        "Isolde serait fière.",
        "Tu as pris leur vie, tu as pris leur corps.",
        "Souverain."
    ],
    "Viktor": [
        "L'Évolution Glorieuse !",
        "Tu as upgrade tes sorts, tu as upgrade la win.",
        "Rayon de la mort : nettoyé.",
        "Chaos Storm parfaite.",
        "Héraut des machines.",
        "Zaun triomphe par la science.",
        "Gravité contrôlée.",
        "Le métal est plus fort que la chair.",
        "Tu as calculé chaque mouvement.",
        "Progrès inarrêtable."
    ],
    "Vladimir": [
        "La rivière sera rouge.",
        "Hémomancien suprême.",
        "Tu as pool leur ulti : génie.",
        "Sustain infini.",
        "Le sang coule à flots.",
        "Late game monster.",
        "Tu as one-shot l'équipe avec E-R.",
        "Seigneur vampire.",
        "Dîner servi.",
        "Vitalité volée."
    ],
    "Volibear": [
        "LA TEMPÊTE APPROCHE !",
        "Le Dieu Ours a écrasé l'idole.",
        "Tu as désactivé la tour, tu as tué le laner.",
        "Foudre et griffes.",
        "Valhir !",
        "Tu as tanké la foudre.",
        "Sauvagerie incarne.",
        "L'orage gronde pour la victoire.",
        "Tu as mordu la poussière... euh non, eux.",
        "Puissance primordiale."
    ],
    "Warwick": [
        "L'odeur du sang...",
        "Tu as traversé la map en sprint.",
        "Loup de Zaun.",
        "Suppression infinie.",
        "Tu refuses de mourir.",
        "Huuuuuuuurl !",
        "La chasse ne s'arrête jamais.",
        "Griffes acérées.",
        "Tu as flairé la victoire.",
        "Bête déchaînée."
    ],
    "Wukong": [
        "Wuju ? Non, Wukong !",
        "Le Roi des Singes a trompé tout le monde.",
        "Clone juke : magnifique.",
        "Le bâton s'allonge, la victoire approche.",
        "Cyclone double knockup.",
        "Tu as spin to win.",
        "Agile et puissant.",
        "Vastaya malicieux.",
        "Tu as atteint le sommet.",
        "La voie du guerrier."
    ],
    "Xayah": [
        "Les plumes ont volé.",
        "Rappel de plumes : Pentakill.",
        "Rebelle Vastaya.",
        "Intouchable avec l'ulti.",
        "Rakan t'a aidée, mais tu as carry.",
        "Danseuse de lames (plumes).",
        "Tu as, percé leurs lignes.",
        "Liberté !",
        "Grâce mortelle.",
        "Plumage d'or."
    ],
    "Xerath": [
        "La forme pure de la magie.",
        "Arcanopulse sniper.",
        "Rite Arcanique : Bombardement.",
        "Tu as touché tous les skillshots.",
        "Ascension ratée ? Non, victoire réussie.",
        "Puissance illimitée.",
        "Tu as foudroyé l'équipe.",
        "Mage d'artillerie.",
        "Sarcophage brisé.",
        "Énergie brute."
    ],
    "XinZhao": [
        "Pour le Roi !",
        "Sénéchal de Demacia.",
        "Tu as foncé dans la mêlée.",
        "Ulti : Zone VIP, vous ne rentrez pas.",
        "Trois coups, un knockup, un mort.",
        "Lancier expert.",
        "Le destin est au bout de ta lance.",
        "Courage sans faille.",
        "Tu as défendu l'honneur.",
        "Guerrier modèle."
    ],
    "Yasuo": [
        "HASAGI !",
        "Sorye Ge Ton !",
        "Mur de vent : 0 dégâts subis.",
        "Tu as atteint le powerspike 0/10 (non je rigole, tu as carry).",
        "Disgracié ? Non, glorifié.",
        "La voie du vagabond.",
        "Tornade touchée, ulti activé.",
        "Dernier Souffle.",
        "Lame du vent.",
        "Face the wind."
    ],
    "Yone": [
        "Un coupé, un scellé.",
        "Le frère est revenu.",
        "Spirit form outplay.",
        "Ulti Fate Sealed sur 5 personnes.",
        "Double épée, double style.",
        "Azakana chassé.",
        "Tu as transcendé la mort.",
        "Assassinat propre.",
        "Vent et Acier.",
        "La voie du chasseur."
    ],
    "Yorick": [
        "La Dame a fait le travail.",
        "Tu as, push jusqu'à l'inhibiteur.",
        "Les goules ont mangé la tour.",
        "Berger des âmes perdues.",
        "Pelle MVP.",
        "Tu as enfermé l'ennemi dans le mur.",
        "Défouisseur victorieux.",
        "L'Île Obscure marche avec toi.",
        "Splitpush inarrêtable.",
        "La fin est inévitable."
    ],
    "Yuumi": [
        "Tu es le chat ! 😺",
        "Livre magique ouvert, victoire ouverte.",
        "Tu as zoomies partout.",
        "Chapitre final : Win.",
        "Le parasite préféré.",
        "Tu as, gardé ton carry en vie.",
        "Miaou !",
        "Chatte magique.",
        "Intouchable (littéralement).",
        "Nous avons gagné ! (Surtout toi)."
    ],
    "Zac": [
        "Je suis fait pour ça... littéralement.",
        "Rebondissement !",
        "Slingshot depuis le fog of war.",
        "L'arme secrète a fonctionné.",
        "Tu as englué l'ennemi.",
        "Pas de costume pour gagner.",
        "Regroupement familial (de blobs).",
        "Tu as tanké et CC.",
        "Flubber de combat.",
        "Élastique et fantastique."
    ],
    "Zed": [
        "L'ombre tue...",
        "Look at the cleanse, look at the moves ! FAKER !",
        "Death Mark : Pop.",
        "Ninja des ombres.",
        "Tu as disparu, ils sont morts.",
        "Maître de l'Ordre.",
        "Shuriken croisé.",
        "L'équilibre est un mensonge, la victoire est vraie.",
        "Intouchable.",
        "Tu es l'ombre qui gagne."
    ],
    "Zeri": [
        "Je suis survoltée !",
        "Vitesse, vitesse, vitesse !",
        "Tu as kité à la vitesse de l'éclair.",
        "Zaunite rapide.",
        "Wall ride pour le flank.",
        "Mitraillette électrique.",
        "Tu as, zappé la concurrence.",
        "Étincelle de vie.",
        "Tu ne t'arrêtes jamais.",
        "Batterie pleine."
    ],
    "Ziggs": [
        "Ça va péter !",
        "BOMBE INTÉGRALE !",
        "Tu as démoli les tours.",
        "Yordle explosif.",
        "Zone minée.",
        "Tu as satchel charge pour t'enfuir (ou tuer).",
        "Expert en Hexplosifs.",
        "Mèche courte.",
        "Feu d'artifice de victoire.",
        "Boum."
    ],
    "Zilean": [
        "Je savais que tu ferais ça.",
        "Retour vers le passé (pour revivre).",
        "Tu as sauvé le carry de la mort.",
        "Double bombe stunlock.",
        "Gardien du Temps.",
        "Tu as contrôlé l'horloge.",
        "Vitesse grand V.",
        "Expérience partagée.",
        "Le temps est de ton côté.",
        "Vieil horloger victorieux."
    ],
    "Zoe": [
        "Coucou !",
        "Bulle dodo... et BOUM.",
        "Tu as volé leurs summoners.",
        "Aspect du Crépuscule.",
        "Paddle Star sniper.",
        "Tu as trollé l'ennemi avec le sourire.",
        "Espace-temps plié.",
        "Petite fille cosmique.",
        "Portail jump outplay.",
        "Chocolat et victoire."
    ],
    "Zyra": [
        "La nature est cruelle... et toi aussi.",
        "Jardin mortel.",
        "Les plantes ont fait le travail.",
        "Stranglethorns !",
        "Épines fatales.",
        "Reine des Ronces.",
        "Tu as, enraciné l'équipe adverse.",
        "Tout pousse, tout meurt.",
        "Floraison de la victoire.",
        "Dame Nature en colère."
    ]
}

if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
else:
    data = {}

data.update(new_praises)

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f"Updated {len(new_praises)} champions.")
