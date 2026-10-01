import os
import csv

SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_dataset"))
os.makedirs(SAMPLE_DIR, exist_ok=True)

articles = [
    # REAL NEWS ARTICLES
    {
        "text": "NASA's James Webb Space Telescope has captured unprecedented images of distant galaxies formed just hundreds of millions of years after the Big Bang. Astronomers confirm that these observations challenge existing cosmological models of early galactic evolution.",
        "label": "REAL"
    },
    {
        "text": "The Federal Reserve announced a quarter-point interest rate adjustment following its two-day policy meeting. Central bank officials stated that inflation indicators have shown steady moderation while labor market conditions remain stable across major metropolitan areas.",
        "label": "REAL"
    },
    {
        "text": "World Health Organization representatives convened in Geneva to discuss updated global guidelines on antibiotic resistance. Medical researchers emphasized that misuse of antimicrobial treatments in livestock and healthcare continues to threaten modern infection management.",
        "label": "REAL"
    },
    {
        "text": "European Union regulators have enacted comprehensive standards governing artificial intelligence systems. The legislation imposes mandatory risk assessments, transparency requirements for foundation models, and prohibitions on biometric surveillance in public spaces.",
        "label": "REAL"
    },
    {
        "text": "A team of marine biologists from the Scripps Institution of Oceanography identified a previously unrecorded species of deep-sea octopod during an expedition to the Clarion-Clipperton Zone in the central Pacific Ocean.",
        "label": "REAL"
    },
    {
        "text": "The national meteorological service issued severe flood warnings for coastal regions following three consecutive days of torrential monsoon rainfall. Local emergency management teams have established temporary shelters and initiated evacuations.",
        "label": "REAL"
    },
    {
        "text": "Renewable energy generation accounted for over thirty percent of total electricity consumption nationwide this quarter, according to data published by the Department of Energy. Solar photovoltaic and onshore wind installations led the expansion.",
        "label": "REAL"
    },
    {
        "text": "Researchers at Oxford University have published clinical trial findings demonstrating that a novel malaria vaccine achieves over seventy-five percent efficacy among young children in seasonal transmission areas across sub-Saharan Africa.",
        "label": "REAL"
    },
    {
        "text": "The United Nations Security Council convened an emergency session to deliberate humanitarian corridors and cease-fire arrangements in conflict-affected border regions, urging all parties to respect international humanitarian conventions.",
        "label": "REAL"
    },
    {
        "text": "Automotive manufacturers reported a substantial increase in electric vehicle shipments following federal tax credit revisions and expanded fast-charging infrastructure along inter-state highway corridors.",
        "label": "REAL"
    },
    {
        "text": "Archaeologists excavating a prehistoric settlement near the Mediterranean coast uncovered ceramic storage vessels containing residue of olive oil and wine dating back more than four thousand years.",
        "label": "REAL"
    },
    {
        "text": "The international consortium of seismologists recorded a magnitude 6.2 earthquake off the coast of Honshu, Japan. Authorities confirmed that tsunami warning systems functioned as designed and no catastrophic coastal damage occurred.",
        "label": "REAL"
    },
    {
        "text": "Global semiconductor fabrication capacity expanded following the commissioning of two advanced manufacturing plants in Arizona and Saxony, intended to alleviate international supply chain bottlenecks for microcontrollers.",
        "label": "REAL"
    },
    {
        "text": "Public health authorities reported a seasonal decline in influenza hospitalizations following widespread community vaccination campaigns and continued adherence to respiratory hygiene standards.",
        "label": "REAL"
    },
    {
        "text": "Agricultural economists released a report indicating that prolonged drought conditions across the Midwest have constrained corn and soybean yields, leading to moderate commodity price volatility on international exchanges.",
        "label": "REAL"
    },
    {
        "text": "The International Telecommunication Union approved harmonized spectrum allocations for next-generation satellite broadband networks to ensure equitable wireless connectivity in remote rural territories.",
        "label": "REAL"
    },
    {
        "text": "Civil engineers completed safety inspections on more than two hundred suspension bridges nationwide, recommending structural reinforcement on thirty-four bridges constructed prior to nineteen seventy.",
        "label": "REAL"
    },
    {
        "text": "A peer-reviewed study in the journal Nature revealed that urban green canopy expansion directly correlates with lower ambient surface temperatures and reduced residential cooling energy consumption during heat waves.",
        "label": "REAL"
    },
    {
        "text": "The national statistics bureau reported consumer price index growth slowed to two point four percent year-over-year, indicating steady progress toward long-term price stability targets.",
        "label": "REAL"
    },
    {
        "text": "Aerospace engineers successfully concluded static fire testing of the cryogenic second-stage rocket engine designed for upcoming robotic lunar cargo delivery missions.",
        "label": "REAL"
    },
    {
        "text": "Wildlife conservation authorities reported a measurable recovery in the endangered snow leopard population across designated high-altitude sanctuary corridors in the Himalayas.",
        "label": "REAL"
    },
    {
        "text": "Municipal transit authorities launched a contactless fare payment system across subway and bus lines to streamline passenger boarding and decrease commuter queue times.",
        "label": "REAL"
    },
    {
        "text": "Medical researchers at Johns Hopkins Medicine identified specific biomarker patterns in blood samples that enable earlier diagnosis of degenerative neuromuscular disorders.",
        "label": "REAL"
    },
    {
        "text": "The international postal union implemented standardized tracking protocols for cross-border electronic commerce packages, reducing parcel transit delays between partner nations.",
        "label": "REAL"
    },
    {
        "text": "Geoscientists conducting core drilling in Antarctica retrieved ice samples containing atmospheric gas records spanning eight hundred thousand years of historical planetary climate cycles.",
        "label": "REAL"
    },

    # FAKE NEWS ARTICLES
    {
        "text": "SHOCKING SECRET EXPOSED: Leaked government documents prove that cellular 5G towers are broadcasting mind-control microwave frequencies to manipulate voter thoughts during general elections. Share before mainstream media deletes this!",
        "label": "FAKE"
    },
    {
        "text": "DOCTORS ARE TERRIFIED: Eating boiled lemon peels and raw garlic with vinegar cures all stages of terminal cancer in twenty-four hours. Pharmaceutical executives are secretly banning this ancient household remedy to protect their trillion dollar profits!",
        "label": "FAKE"
    },
    {
        "text": "BREAKING BOMBSHELL: NASA admits that the Apollo moon landings were completely filmed in a secret soundstage in Hollywood directed by Stanley Kubrick. Whistleblower reveals original props were stored in an abandoned desert bunker!",
        "label": "FAKE"
    },
    {
        "text": "URGENT ALERT: Bill Gates admits in leaked video that microchips are being secretly injected into ordinary bottled drinking water to track every citizen's GPS location and credit card spending habits.",
        "label": "FAKE"
    },
    {
        "text": "ALIEN AUTOPSY CONFIRMED: Scientists at a military base in Nevada have captured an extraterrestrial being alive after an unidentified flying saucer crashed in the desert. World leaders are hiding the discovery until next month!",
        "label": "FAKE"
    },
    {
        "text": "MIRACLE WEALTH FORMULA: Financial billionaires reveal an automated secret loophole that guarantees ten thousand dollars a day to anyone who clicks this link. Banks are desperately attempting to shut down this website right now!",
        "label": "FAKE"
    },
    {
        "text": "TERRIFYING TRUTH: Tap water contains synthetic chemical compounds specifically engineered by global elites to lower human intelligence and turn citizens into docile government obedience drones. Stop drinking tap water immediately!",
        "label": "FAKE"
    },
    {
        "text": "CELEBRITY EXPOSURE: Hollywood superstar arrested after exposing secret subterranean tunnel network beneath royal palace where politicians perform dark rituals every solstice. The mainstream press has issued a total gag order!",
        "label": "FAKE"
    },
    {
        "text": "PROVEN AT LAST: Top secret satellite images confirm that the Earth is entirely flat and surrounded by a giant impenetrable ice wall guarded by armed international naval warships. NASA is covering up the truth!",
        "label": "FAKE"
    },
    {
        "text": "UNBELIEVABLE DISCOVERY: Ancient Egyptian pyramids were built as intergalactic wireless power transmitters by time travelers from the year 3000. Historians are hiding the truth to preserve historical textbooks!",
        "label": "FAKE"
    },
    {
        "text": "DEADLY HAZARD: Wearing Bluetooth earphones radiates brain tissue directly and replaces your natural cerebral fluid with toxic synthetic gelatin. Over fifty thousand victims hospitalized according to anonymous insider nurse!",
        "label": "FAKE"
    },
    {
        "text": "GOVERNMENT CONSPIRACY: Weather control machines operated from an underground base in Alaska deliberately triggered the recent hurricane to wipe out conservative farm districts before crop harvest. Must read and spread the truth!",
        "label": "FAKE"
    },
    {
        "text": "SECRET CURE HIDDEN: Putting slices of raw red onion inside your socks overnight extracts all deadly toxins, eliminates diabetes, and restores twenty-twenty vision. Big Pharma does not want you knowing this one weird trick!",
        "label": "FAKE"
    },
    {
        "text": "SHOCKING REPORT: World Economic Forum officially mandates that all citizens must replace meat with laboratory-grown cockroach flour by next December or face immediate freezing of personal bank accounts.",
        "label": "FAKE"
    },
    {
        "text": "CONFIDENTIAL FILES LEAKED: Deep state operatives accidentally published blueprint for replacing wild birds with solar-powered surveillance drones equipped with facial recognition microphones.",
        "label": "FAKE"
    },
    {
        "text": "PANIC IN CAPITOL: Prime Minister caught on hot mic admitting that national currency will be abolished tomorrow morning and all bank deposits confiscated by international central banking cabal. Forward to everyone!",
        "label": "FAKE"
    },
    {
        "text": "MIRACLE DIET DISCOVERY: Drinking warm salt water mixed with baking soda melts thirty pounds of belly fat in forty-eight hours without exercise. Banned by television networks because doctors complained!",
        "label": "FAKE"
    },
    {
        "text": "ALERT: Secret satellite lasers owned by foreign billionaires are causing localized wildfire disasters to devalue land for private luxury resort development. The evidence has been completely scrubbed from search engines!",
        "label": "FAKE"
    },
    {
        "text": "EXTREME WARNING: Eating commercial bananas injects synthetic snake venom directly into your bloodstream. Supermarket workers warned of massive cover-up after thousands reported glowing green eyes.",
        "label": "FAKE"
    },
    {
        "text": "LEAKED AUDIO TAPE: Global pharmaceutical CEO laughs about putting microscopic tracking nanobots in routine headache painkillers to monitor household conversations. Listen before it gets taken down!",
        "label": "FAKE"
    },
    {
        "text": "BREAKING: Scientists discover immortal human living in hidden cave in the Amazon jungle who has not eaten food or drunk water for four hundred years using secret magnetic breathing frequency.",
        "label": "FAKE"
    },
    {
        "text": "TOTAL CHAOS: Central intelligence agency admitted in declassified memo that dinosaur fossils were made in plastic factories during the Great Depression to invent evolutionary science and fool taxpayers.",
        "label": "FAKE"
    },
    {
        "text": "SCANDAL OF THE CENTURY: Prominent television news anchor reveals on deathbed that every single major world event since 1990 was scripted by an underground committee of occult stage directors.",
        "label": "FAKE"
    },
    {
        "text": "DEADLY WARNING: Charging your smartphone next to a houseplant creates toxic ionizing electromagnetic plasma that suffocates pets and family members while sleeping. Share this life-saving warning with loved ones immediately!",
        "label": "FAKE"
    },
    {
        "text": "BOMBSHELL EVIDENCE: Newly uncovered treaty proves Antarctica is not a continent but an entrance to an inner hollow earth empire populated by advanced civilizations with flying electromagnetic discs.",
        "label": "FAKE"
    }
]

# Write CSV
csv_path = os.path.join(SAMPLE_DIR, "labeled_news_dataset.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["text", "label"])
    writer.writeheader()
    for row in articles:
        writer.writerow(row)

print(f"Created {csv_path} with {len(articles)} sample rows.")

# Write sample real news txt file for file upload testing
real_txt_path = os.path.join(SAMPLE_DIR, "test_real_article.txt")
with open(real_txt_path, "w", encoding="utf-8") as f:
    f.write("NASA astronomers have released new high-resolution spectroscopic data from the James Webb Space Telescope. The observations identify water vapor, sulfur dioxide, and carbon monoxide in the atmosphere of an exoplanet orbiting a sun-like star seventy light-years away. The scientific community praised the findings as a major milestone for exoplanet atmospheric research.")

# Write sample fake news txt file for file upload testing
fake_txt_path = os.path.join(SAMPLE_DIR, "test_fake_article.txt")
with open(fake_txt_path, "w", encoding="utf-8") as f:
    f.write("SHOCKING BOMBSHELL: Leaked military documents prove that global telecommunication satellites are broadcasting secret mind-control frequencies directly into household smart meters. Whistleblower reveals that tap water is intentionally fluoridated to make citizens docile. Share this urgent warning before government censors delete this page forever!")

print("Created sample test txt files.")
