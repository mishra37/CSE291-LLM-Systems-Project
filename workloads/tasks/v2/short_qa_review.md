QA prompts and references are unchanged from v1; only collection IDs/version metadata differ.

# Short QA: 20 examples

The complete short-QA development collection: 20 different passages and topics, one model call per task, and no tools. Flag any issue by task ID.

**Model instruction:** Answer the question using only the passage. Return only the shortest answer span from the passage, with no explanation.

**Proposed generation:** temperature 0, maximum 32 tokens, natural EOS stopping. AWS inference and exact tokenizer checks have not been performed.

The model receives the passage and question. Reference answers and source metadata are evaluator-only. Answers refer to the supplied historical SQuAD passages; this is not a test of current world knowledge.

## Index

| Task | Topic | Question | Reference answer |
|---|---|---|---|
| [short_qa-v2-001](#short_qa-v2-001) | Super Bowl 50 | Which NFL team won Super Bowl 50? | Denver Broncos |
| [short_qa-v2-002](#short_qa-v2-002) | Oxygen | What is the atomic number for oxygen? | 8 |
| [short_qa-v2-003](#short_qa-v2-003) | Normans | In what country is Normandy located? | France |
| [short_qa-v2-004](#short_qa-v2-004) | Nikola Tesla | In what year did Nikola Tesla emigrate to the United States? | 1884 |
| [short_qa-v2-005](#short_qa-v2-005) | Computational complexity theory | What branch of theoretical computer science deals with broadly classifying computational problems by difficulty and class of relationship? | Computational complexity theory |
| [short_qa-v2-006](#short_qa-v2-006) | Steam engine | Who was the inventor of the atmospheric engine? | Thomas Newcomen |
| [short_qa-v2-007](#short_qa-v2-007) | Apollo program | What space station supported three manned missions in 1973-1974? | Skylab |
| [short_qa-v2-008](#short_qa-v2-008) | Amazon rainforest | In what country can most of the Amazon rainforest be found? | Brazil |
| [short_qa-v2-009](#short_qa-v2-009) | Warsaw | How old was Chopin when he moved to Warsaw with his family? | seven months old |
| [short_qa-v2-010](#short_qa-v2-010) | Geology | Whose theory was the theory of continental drift? | Alfred Wegener |
| [short_qa-v2-011](#short_qa-v2-011) | Victoria and Albert Museum | In what year was the Victoria and Albert Museum founded? | 1852 |
| [short_qa-v2-012](#short_qa-v2-012) | Genghis Khan | Who did Genghis Khan assign as his successor? | Ögedei Khan |
| [short_qa-v2-013](#short_qa-v2-013) | Immune system | What are the agents the immune system detects known as? | pathogens |
| [short_qa-v2-014](#short_qa-v2-014) | Harvard University | In what year was the school renamed as Harvard College? | 1639 |
| [short_qa-v2-015](#short_qa-v2-015) | Doctor Who | What is Doctor Who's space ship called? | TARDIS |
| [short_qa-v2-016](#short_qa-v2-016) | University of Chicago | How many academic research divisions does the University of Chicago have? | four |
| [short_qa-v2-017](#short_qa-v2-017) | Chloroplast | How do chloroplasts reproduce? | pinch in two |
| [short_qa-v2-018](#short_qa-v2-018) | Prime number | What is the only divisor besides 1 that a prime number can have? | itself |
| [short_qa-v2-019](#short_qa-v2-019) | Rhine | What is the Rhine called in French? | Rhin |
| [short_qa-v2-020](#short_qa-v2-020) | Construction | The largest construction projects are known as what? | megaprojects |

## short_qa-v2-001

**Topic:** Super Bowl 50 | **Answer type:** entity | **Passage words:** 124

**Passage:**

Super Bowl 50 was an American football game to determine the champion of the National Football League (NFL) for the 2015 season. The American Football Conference (AFC) champion Denver Broncos defeated the National Football Conference (NFC) champion Carolina Panthers 24–10 to earn their third Super Bowl title. The game was played on February 7, 2016, at Levi's Stadium in the San Francisco Bay Area at Santa Clara, California. As this was the 50th Super Bowl, the league emphasized the "golden anniversary" with various gold-themed initiatives, as well as temporarily suspending the tradition of naming each Super Bowl game with Roman numerals (under which the game would have been known as "Super Bowl L"), so that the logo could prominently feature the Arabic numerals 50.

**Question:** Which NFL team won Super Bowl 50?

**Reference answer:** Denver Broncos

**Source:** SQuAD 1.1 dev, question `56be4db0acb8001400a502ef`. All 3 original annotations agree on the answer text.

## short_qa-v2-002

**Topic:** Oxygen | **Answer type:** quantity | **Passage words:** 135

**Passage:**

Oxygen is a chemical element with symbol O and atomic number 8. It is a member of the chalcogen group on the periodic table and is a highly reactive nonmetal and oxidizing agent that readily forms compounds (notably oxides) with most elements. By mass, oxygen is the third-most abundant element in the universe, after hydrogen and helium. At standard temperature and pressure, two atoms of the element bind to form dioxygen, a colorless and odorless diatomic gas with the formula O
2. Diatomic oxygen gas constitutes 20.8% of the Earth's atmosphere. However, monitoring of atmospheric oxygen levels show a global downward trend, because of fossil-fuel burning. Oxygen is the most abundant element by mass in the Earth's crust as part of oxide compounds such as silicon dioxide, making up almost half of the crust's mass.

**Question:** What is the atomic number for oxygen?

**Reference answer:** 8

**Source:** SQuAD 1.1 dev, question `571bb2269499d21900609cab`. All 5 original annotations agree on the answer text.

## short_qa-v2-003

**Topic:** Normans | **Answer type:** location | **Passage words:** 113

**Passage:**

The Normans (Norman: Nourmands; French: Normands; Latin: Normanni) were the people who in the 10th and 11th centuries gave their name to Normandy, a region in France. They were descended from Norse ("Norman" comes from "Norseman") raiders and pirates from Denmark, Iceland and Norway who, under their leader Rollo, agreed to swear fealty to King Charles III of West Francia. Through generations of assimilation and mixing with the native Frankish and Roman-Gaulish populations, their descendants would gradually merge with the Carolingian-based cultures of West Francia. The distinct cultural and ethnic identity of the Normans emerged initially in the first half of the 10th century, and it continued to evolve over the succeeding centuries.

**Question:** In what country is Normandy located?

**Reference answer:** France

**Source:** SQuAD 1.1 dev, question `56ddde6b9a695914005b9628`. All 4 original annotations agree on the answer text.

## short_qa-v2-004

**Topic:** Nikola Tesla | **Answer type:** year | **Passage words:** 97

**Passage:**

Tesla gained experience in telephony and electrical engineering before emigrating to the United States in 1884 to work for Thomas Edison in New York City. He soon struck out on his own with financial backers, setting up laboratories and companies to develop a range of electrical devices. His patented AC induction motor and transformer were licensed by George Westinghouse, who also hired Tesla for a short time as a consultant. His work in the formative years of electric power development was involved in a corporate alternating current/direct current "War of Currents" as well as various patent battles.

**Question:** In what year did Nikola Tesla emigrate to the United States?

**Reference answer:** 1884

**Source:** SQuAD 1.1 dev, question `56df9ee138dc421700152108`. All 3 original annotations agree on the answer text.

## short_qa-v2-005

**Topic:** Computational complexity theory | **Answer type:** term | **Passage words:** 74

**Passage:**

Computational complexity theory is a branch of the theory of computation in theoretical computer science that focuses on classifying computational problems according to their inherent difficulty, and relating those classes to each other. A computational problem is understood to be a task that is in principle amenable to being solved by a computer, which is equivalent to stating that the problem may be solved by mechanical application of mathematical steps, such as an algorithm.

**Question:** What branch of theoretical computer science deals with broadly classifying computational problems by difficulty and class of relationship?

**Reference answer:** Computational complexity theory

**Source:** SQuAD 1.1 dev, question `56e16182e3433e1400422e28`. All 3 original annotations agree on the answer text.

## short_qa-v2-006

**Topic:** Steam engine | **Answer type:** person | **Passage words:** 121

**Passage:**

The first commercially successful true engine, in that it could generate power and transmit it to a machine, was the atmospheric engine, invented by Thomas Newcomen around 1712. It was an improvement over Savery's steam pump, using a piston as proposed by Papin. Newcomen's engine was relatively inefficient, and in most cases was used for pumping water. It worked by creating a partial vacuum by condensing steam under a piston within a cylinder. It was employed for draining mine workings at depths hitherto impossible, and also for providing a reusable water supply for driving waterwheels at factories sited away from a suitable "head". Water that had passed over the wheel was pumped back up into a storage reservoir above the wheel.

**Question:** Who was the inventor of the atmospheric engine?

**Reference answer:** Thomas Newcomen

**Source:** SQuAD 1.1 dev, question `571126dfa58dae1900cd6cb3`. All 4 original annotations agree on the answer text.

## short_qa-v2-007

**Topic:** Apollo program | **Answer type:** entity | **Passage words:** 90

**Passage:**

Apollo ran from 1961 to 1972, and was supported by the two-man Gemini program which ran concurrently with it from 1962 to 1966. Gemini missions developed some of the space travel techniques that were necessary for the success of the Apollo missions. Apollo used Saturn family rockets as launch vehicles. Apollo/Saturn vehicles were also used for an Apollo Applications Program, which consisted of Skylab, a space station that supported three manned missions in 1973–74, and the Apollo–Soyuz Test Project, a joint Earth orbit mission with the Soviet Union in 1975.

**Question:** What space station supported three manned missions in 1973-1974?

**Reference answer:** Skylab

**Source:** SQuAD 1.1 dev, question `5725b56589a1e219009abd23`. All 5 original annotations agree on the answer text.

## short_qa-v2-008

**Topic:** Amazon rainforest | **Answer type:** location | **Passage words:** 156

**Passage:**

The Amazon rainforest (Portuguese: Floresta Amazônica or Amazônia; Spanish: Selva Amazónica, Amazonía or usually Amazonia; French: Forêt amazonienne; Dutch: Amazoneregenwoud), also known in English as Amazonia or the Amazon Jungle, is a moist broadleaf forest that covers most of the Amazon basin of South America. This basin encompasses 7,000,000 square kilometres (2,700,000 sq mi), of which 5,500,000 square kilometres (2,100,000 sq mi) are covered by the rainforest. This region includes territory belonging to nine nations. The majority of the forest is contained within Brazil, with 60% of the rainforest, followed by Peru with 13%, Colombia with 10%, and with minor amounts in Venezuela, Ecuador, Bolivia, Guyana, Suriname and French Guiana. States or departments in four nations contain "Amazonas" in their names. The Amazon represents over half of the planet's remaining rainforests, and comprises the largest and most biodiverse tract of tropical rainforest in the world, with an estimated 390 billion individual trees divided into 16,000 species.

**Question:** In what country can most of the Amazon rainforest be found?

**Reference answer:** Brazil

**Source:** SQuAD 1.1 dev, question `5728349dff5b5019007d9f00`. All 3 original annotations agree on the answer text.

## short_qa-v2-009

**Topic:** Warsaw | **Answer type:** quantity | **Passage words:** 87

**Passage:**

One of the most famous people born in Warsaw was Maria Skłodowska-Curie, who achieved international recognition for her research on radioactivity and was the first female recipient of the Nobel Prize. Famous musicians include Władysław Szpilman and Frédéric Chopin. Though Chopin was born in the village of Żelazowa Wola, about 60 km (37 mi) from Warsaw, he moved to the city with his family when he was seven months old. Casimir Pulaski, a Polish general and hero of the American Revolutionary War, was born here in 1745.

**Question:** How old was Chopin when he moved to Warsaw with his family?

**Reference answer:** seven months old

**Source:** SQuAD 1.1 dev, question `5733a5f54776f41900660f47`. All 3 original annotations agree on the answer text.

## short_qa-v2-010

**Topic:** Geology | **Answer type:** person | **Passage words:** 158

**Passage:**

The development of plate tectonics provided a physical basis for many observations of the solid Earth. Long linear regions of geologic features could be explained as plate boundaries. Mid-ocean ridges, high regions on the seafloor where hydrothermal vents and volcanoes exist, were explained as divergent boundaries, where two plates move apart. Arcs of volcanoes and earthquakes were explained as convergent boundaries, where one plate subducts under another. Transform boundaries, such as the San Andreas fault system, resulted in widespread powerful earthquakes. Plate tectonics also provided a mechanism for Alfred Wegener's theory of continental drift, in which the continents move across the surface of the Earth over geologic time. They also provided a driving force for crustal deformation, and a new setting for the observations of structural geology. The power of the theory of plate tectonics lies in its ability to combine all of these observations into a single theory of how the lithosphere moves over the convecting mantle.

**Question:** Whose theory was the theory of continental drift?

**Reference answer:** Alfred Wegener

**Source:** SQuAD 1.1 dev, question `57265f605951b619008f70de`. All 4 original annotations agree on the answer text.

## short_qa-v2-011

**Topic:** Victoria and Albert Museum | **Answer type:** year | **Passage words:** 132

**Passage:**

The Victoria and Albert Museum (often abbreviated as the V&A), London, is the world's largest museum of decorative arts and design, housing a permanent collection of over 4.5 million objects. It was founded in 1852 and named after Queen Victoria and Prince Albert. The V&A is located in the Brompton district of the Royal Borough of Kensington and Chelsea, in an area that has become known as "Albertopolis" because of its association with Prince Albert, the Albert Memorial and the major cultural institutions with which he was associated. These include the Natural History Museum, the Science Museum and the Royal Albert Hall. The museum is a non-departmental public body sponsored by the Department for Culture, Media and Sport. Like other national British museums, entrance to the museum has been free since 2001.

**Question:** In what year was the Victoria and Albert Museum founded?

**Reference answer:** 1852

**Source:** SQuAD 1.1 dev, question `572680ac708984140094c83e`. All 4 original annotations agree on the answer text.

## short_qa-v2-012

**Topic:** Genghis Khan | **Answer type:** person | **Passage words:** 110

**Passage:**

Before Genghis Khan died, he assigned Ögedei Khan as his successor and split his empire into khanates among his sons and grandsons. He died in 1227 after defeating the Western Xia. He was buried in an unmarked grave somewhere in Mongolia at an unknown location. His descendants extended the Mongol Empire across most of Eurasia by conquering or creating vassal states out of all of modern-day China, Korea, the Caucasus, Central Asia, and substantial portions of modern Eastern Europe, Russia, and Southwest Asia. Many of these invasions repeated the earlier large-scale slaughters of local populations. As a result, Genghis Khan and his empire have a fearsome reputation in local histories.

**Question:** Who did Genghis Khan assign as his successor?

**Reference answer:** Ögedei Khan

**Source:** SQuAD 1.1 dev, question `5726a00d708984140094cc25`. All 3 original annotations agree on the answer text.

## short_qa-v2-013

**Topic:** Immune system | **Answer type:** term | **Passage words:** 102

**Passage:**

The immune system is a system of many biological structures and processes within an organism that protects against disease. To function properly, an immune system must detect a wide variety of agents, known as pathogens, from viruses to parasitic worms, and distinguish them from the organism's own healthy tissue. In many species, the immune system can be classified into subsystems, such as the innate immune system versus the adaptive immune system, or humoral immunity versus cell-mediated immunity. In humans, the blood–brain barrier, blood–cerebrospinal fluid barrier, and similar fluid–brain barriers separate the peripheral immune system from the neuroimmune system which protects the brain.

**Question:** What are the agents the immune system detects known as?

**Reference answer:** pathogens

**Source:** SQuAD 1.1 dev, question `5728eff82ca10214002daadd`. All 4 original annotations agree on the answer text.

## short_qa-v2-014

**Topic:** Harvard University | **Answer type:** year | **Passage words:** 95

**Passage:**

Harvard was formed in 1636 by vote of the Great and General Court of the Massachusetts Bay Colony. It was initially called "New College" or "the college at New Towne". In 1638, the college became home for North America's first known printing press, carried by the ship John of London. In 1639, the college was renamed Harvard College after deceased clergyman John Harvard, who was an alumnus of the University of Cambridge. He had left the school £779 and his library of some 400 books. The charter creating the Harvard Corporation was granted in 1650.

**Question:** In what year was the school renamed as Harvard College?

**Reference answer:** 1639

**Source:** SQuAD 1.1 dev, question `5727afa82ca10214002d93c5`. All 3 original annotations agree on the answer text.

## short_qa-v2-015

**Topic:** Doctor Who | **Answer type:** entity | **Passage words:** 85

**Passage:**

Doctor Who is a British science-fiction television programme produced by the BBC since 1963. The programme depicts the adventures of the Doctor, a Time Lord—a space and time-travelling humanoid alien. He explores the universe in his TARDIS, a sentient time-travelling space ship. Its exterior appears as a blue British police box, which was a common sight in Britain in 1963 when the series first aired. Accompanied by companions, the Doctor combats a variety of foes, while working to save civilisations and help people in need.

**Question:** What is Doctor Who's space ship called?

**Reference answer:** TARDIS

**Source:** SQuAD 1.1 dev, question `5727efabff5b5019007d98e4`. All 3 original annotations agree on the answer text.

## short_qa-v2-016

**Topic:** University of Chicago | **Answer type:** quantity | **Passage words:** 114

**Passage:**

The University of Chicago (UChicago, Chicago, or U of C) is a private research university in Chicago. The university, established in 1890, consists of The College, various graduate programs, interdisciplinary committees organized into four academic research divisions and seven professional schools. Beyond the arts and sciences, Chicago is also well known for its professional schools, which include the Pritzker School of Medicine, the University of Chicago Booth School of Business, the Law School, the School of Social Service Administration, the Harris School of Public Policy Studies, the Graham School of Continuing Liberal and Professional Studies and the Divinity School. The university currently enrolls approximately 5,000 students in the College and around 15,000 students overall.

**Question:** How many academic research divisions does the University of Chicago have?

**Reference answer:** four

**Source:** SQuAD 1.1 dev, question `57283c464b864d19001647cb`. All 4 original annotations agree on the answer text.

## short_qa-v2-017

**Topic:** Chloroplast | **Answer type:** process | **Passage words:** 77

**Passage:**

Chloroplasts are highly dynamic—they circulate and are moved around within plant cells, and occasionally pinch in two to reproduce. Their behavior is strongly influenced by environmental factors like light color and intensity. Chloroplasts, like mitochondria, contain their own DNA, which is thought to be inherited from their ancestor—a photosynthetic cyanobacterium that was engulfed by an early eukaryotic cell. Chloroplasts cannot be made by the plant cell and must be inherited by each daughter cell during cell division.

**Question:** How do chloroplasts reproduce?

**Reference answer:** pinch in two

**Source:** SQuAD 1.1 dev, question `5729544c3f37b31900478257`. All 3 original annotations agree on the answer text.

## short_qa-v2-018

**Topic:** Prime number | **Answer type:** property | **Passage words:** 146

**Passage:**

A prime number (or a prime) is a natural number greater than 1 that has no positive divisors other than 1 and itself. A natural number greater than 1 that is not a prime number is called a composite number. For example, 5 is prime because 1 and 5 are its only positive integer factors, whereas 6 is composite because it has the divisors 2 and 3 in addition to 1 and 6. The fundamental theorem of arithmetic establishes the central role of primes in number theory: any integer greater than 1 can be expressed as a product of primes that is unique up to ordering. The uniqueness in this theorem requires excluding 1 as a prime because one can include arbitrarily many instances of 1 in any factorization, e.g., 3, 1 · 3, 1 · 1 · 3, etc. are all valid factorizations of 3.

**Question:** What is the only divisor besides 1 that a prime number can have?

**Reference answer:** itself

**Source:** SQuAD 1.1 dev, question `57296d571d04691400779413`. All 5 original annotations agree on the answer text.

## short_qa-v2-019

**Topic:** Rhine | **Answer type:** term | **Passage words:** 153

**Passage:**

The variant forms of the name of the Rhine in modern languages are all derived from the Gaulish name Rēnos, which was adapted in Roman-era geography (1st century BC) as Greek Ῥῆνος (Rhēnos), Latin Rhenus.[note 3] The spelling with Rh- in English Rhine as well as in German Rhein and French Rhin is due to the influence of Greek orthography, while the vocalisation -i- is due to the Proto-Germanic adoption of the Gaulish name as *Rīnaz, via Old Frankish giving Old English Rín, Old High German Rīn, Dutch Rijn (formerly also spelled Rhijn)). The diphthong in modern German Rhein (also adopted in Romansh Rein, Rain) is a Central German development of the early modern period, the Alemannic name Rī(n) retaining the older vocalism,[note 4] as does Ripuarian Rhing, while Palatine has diphthongized Rhei, Rhoi. Spanish is with French in adopting the Germanic vocalism Rin-, while Italian, Occitan and Portuguese retain the Latin Ren-.

**Question:** What is the Rhine called in French?

**Reference answer:** Rhin

**Source:** SQuAD 1.1 dev, question `572fe288a23a5019007fcad8`. All 5 original annotations agree on the answer text.

## short_qa-v2-020

**Topic:** Construction | **Answer type:** term | **Passage words:** 92

**Passage:**

Large-scale construction requires collaboration across multiple disciplines. An architect normally manages the job, and a construction manager, design engineer, construction engineer or project manager supervises it. For the successful execution of a project, effective planning is essential. Those involved with the design and execution of the infrastructure in question must consider zoning requirements, the environmental impact of the job, the successful scheduling, budgeting, construction-site safety, availability and transportation of building materials, logistics, inconvenience to the public caused by construction delays and bidding, etc. The largest construction projects are referred to as megaprojects.

**Question:** The largest construction projects are known as what?

**Reference answer:** megaprojects

**Source:** SQuAD 1.1 dev, question `57273cca708984140094db36`. All 3 original annotations agree on the answer text.

## Attribution

Selected from [SQuAD 1.1 development data](https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v1.1.json), by Rajpurkar et al., with Wikipedia-derived passages. Dataset excerpts remain under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Selection and project metadata were added; passages, questions, and annotations are unchanged. See [workload documentation](../../README.md) for the validation and execution plan.
