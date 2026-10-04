# Feature Specification: Rental Housing Law Navigator

**Feature Branch**: `001-housing-law-navigator`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Build the Rental Housing Law Navigator from the challenge brief and starter pack: for any sample apartment address, state which housing rules apply on the query date, with citations, and how the five supplied change cases affect that answer."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cited rule catalog (Priority: P1)

A reviewer can read a catalog of housing rules drawn from the supplied public corpus. Each rule is one record: where it applies, what it requires, who is covered, who is exempt, whether it is in force, and the exact source passage that supports it.

**Why this priority**: Accurate extraction and citations are the minimum useful result. The catalog stands on its own before any address is looked up, and Santa Ana rules exist only in this catalog.

**Independent Test**: Review the catalog with no address sample. Confirm that each record names its jurisdiction, category, status, requirement, coverage, exemptions, citation, source, retrieval date, and a quoted passage copied from that source.

**Acceptance Scenarios**:

1. **Given** a supplied corpus document that states a housing rule in one of the six categories, **When** the catalog is produced, **Then** that rule appears as its own record with a quoted passage of at least 20 characters taken from the document.
2. **Given** a source that is listed without supplied text, **When** the catalog is produced, **Then** no rule is created from that source and no passage is invented for it.
3. **Given** the default date 2026-10-01, **When** a rule is recorded, **Then** its status is exactly one of in force, not yet effective, pending, or failed.
4. **Given** a Santa Ana ordinance in the corpus, **When** the catalog is produced, **Then** the Santa Ana rule is present even though no sample address is in Santa Ana.

---

### User Story 2 - Address answer on a date (Priority: P1)

A renter, advocate, or housing provider can take one sample apartment address and a date and see which rules apply there, in plain language, with a citation. If a coverage test needs a fact the sample does not have, the answer says unknown and names the missing fact.

**Why this priority**: This is the question the product exists to answer. Together with the catalog, it is the minimum viable submission.

**Independent Test**: Choose one sample address and 2026-10-01. The answer names the legal state, county, and city, lists only the rules that apply or cannot be decided, explains each result in plain language, and shows the as-of date. The screen states that the answer is not legal advice.

**Acceptance Scenarios**:

1. **Given** a sample address whose mailing city is not the legal city, **When** the address is looked up, **Then** coverage is tested against the legal city, county, and state, and the mailing city is not treated as the jurisdiction.
2. **Given** an address inside a city with a local rule and a broader state rule, **When** the stricter local rule governs, **Then** the local rule applies and the state rule is reported as superseded, with the relationship recorded.
3. **Given** an address whose coverage depends on year built, unit count, certificate of occupancy, or owner type, and that fact is missing or is only a construction year in a certificate-of-occupancy cutoff year, **When** the address is looked up, **Then** the result is unknown and the explanation names the missing fact.
4. **Given** a rule that does not cover the address, **When** the lookup is returned, **Then** that rule is omitted.
5. **Given** any person-facing answer, **When** it is shown, **Then** it displays the as-of date, the citation and retrieval date for each rule, and a statement that the output is not legal advice and not a compliance certification.

---

### User Story 3 - Supplied change cases (Priority: P2)

A reviewer can see which of the 500 sample addresses each supplied law-change case affects, which addresses need a human conflict review, and a short note of why.

**Why this priority**: Change tracking is required for a complete submission and comes after extraction and address lookup. The five cases are already defined, so the outcome is checkable without a new surprise document.

**Independent Test**: Run the five cases below and compare the affected addresses and conflict flags with the expected behavior. No other change cases are required.

**Acceptance Scenarios**:

1. **Given** California AB 325 / SB 763, **When** the date is 2025-12-31, **Then** the rule is not yet effective for every California sample address. **When** the date is 2026-01-02, **Then** it applies for every California sample address.
2. **Given** the Hoboken and Jersey City local algorithmic bans on 2026-10-01, **When** addresses are compared, **Then** the Hoboken ban applies only in Hoboken, the Jersey City ban applies only in Jersey City, and neither applies in Newark.
3. **Given** the New Jersey FAIR Act, **When** the date is 2026-10-01, **Then** it is not yet effective for every New Jersey sample address. **When** the date is 2027-07-02, **Then** it applies for every New Jersey sample address, and Jersey City and Hoboken addresses are flagged for a possible conflict with the local bans.
4. **Given** Massachusetts bills S.2983 and H.5222 on 2026-10-01, **When** the case is reported, **Then** both are pending, and the set of addresses they would affect if enacted is every Massachusetts sample address.
5. **Given** the Massachusetts rent-control ballot question on 2026-10-01, **When** the case is reported, **Then** the question is failed, no rent cap is reported for Boston or Cambridge, and the affected set is empty.

---

### Edge Cases

- A mailing city such as Van Nuys or Dorchester is inside a different legal city. The legal city controls coverage.
- San Diego and Berkeley sample rows have no year built. Berkeley also has no unit count. Boston apartment rows, Jersey City, Newark, and most Hoboken rows have no unit count. New Jersey construction years are often missing. A coverage test that needs one of these facts returns unknown.
- Year built is not a certificate of occupancy. San Francisco's cutoff is on or before 1979-06-13, and Los Angeles's cutoff is on or before 1978-10-01. A building in the cutoff year is unknown.
- The sample has no owner names. An exception that depends on owner type, including a small-landlord exception, is unknown.
- Santa Ana rules are extracted and are never attached to a sample address.
- Two published dates exist for Berkeley's algorithmic ban and for Los Angeles's new rent-stabilization formula. The answer flags the conflict for human review and does not pick a date silently.
- The New Jersey FAIR Act may preempt the Jersey City and Hoboken ordinances once it takes effect. Those addresses carry a conflict flag.
- California's screening-fee cap has no single official 2026 dollar figure. The answer does not invent one.
- A query date other than 2026-10-01 changes status only where an effective date, enactment date, or failure date requires it.
- A pending bill is not reported as in force. A failed measure is not reported as a rent cap.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST produce one rule record for each housing rule it reads in the supplied corpus, limited to the six categories: rent increase limits, just-cause eviction, security deposits, application and screening fees, screening restrictions, and algorithmic rent-setting.
- **FR-002**: Each rule record MUST include a unique identifier, jurisdiction, level (state or city), category, status, title, plain-language requirement, citation, source location, retrieval date, and a quoted passage of at least 20 characters copied from the source.
- **FR-003**: Each rule record MUST record coverage conditions and exemptions when the source states them, and MUST record which other rule it supersedes or yields to when the sources say so.
- **FR-004**: Rule text MUST come from automated reading of the supplied corpus. A person MAY correct a record only by tying the correction to a source passage that was read. The system MUST NOT invent a rule, a citation, or a quoted passage.
- **FR-005**: Sources supplied only as links, including publisher pages whose terms were not cleared, MUST NOT be scraped or turned into rule text.
- **FR-006**: The system MUST resolve each sample address to its legal state, county, and city before testing coverage. The mailing city MUST NOT be used as the legal city.
- **FR-007**: For the default date 2026-10-01, the system MUST return a lookup for every one of the 500 sample addresses. Each listed rule MUST have a result of applies, unknown, superseded, not yet effective, or pending, plus a plain-language explanation and a conflict flag.
- **FR-008**: The lookup MUST omit rules that do not apply to that address.
- **FR-009**: When coverage depends on a fact the sample does not contain, the result MUST be unknown and the explanation MUST name the missing fact. Construction year MUST NOT be treated as a certificate-of-occupancy date.
- **FR-010**: The system MUST keep enacted law, not-yet-effective law, pending bills, and failed measures distinct. Possible preemption or conflicting published dates MUST set the conflict flag for human review.
- **FR-011**: The system MUST report the five supplied change cases, listing affected sample addresses, addresses that need a conflict review, and a note for each case. The expected behavior is the behavior in User Story 3.
- **FR-012**: Every person-facing view MUST show the as-of date and MUST state that the output is not legal advice and not a compliance certification. The system MUST NOT suggest a way to avoid a rule.
- **FR-013**: The system MUST keep an audit record for each answer so a second person can see the source, the retrieval date, the as-of date, and the coverage reasoning.
- **FR-014**: The submission MUST include the rule catalog, the address lookup report for all 500 addresses, the change-case report, a demonstration that rules were read from the corpus, and a one-page method note.
- **FR-015**: The system MUST use only the supplied starter pack and public information. It MUST NOT use resident, customer, or pricing data.

### Key Entities

- **Source document**: A public statute, ordinance, bill, or official page in the supplied corpus, identified by document id, jurisdiction, location, and retrieval date. Some documents have text; some are links only.
- **Rule record**: One housing rule extracted from a source document, with jurisdiction, level, category, status, requirement, coverage, exemptions, interactions with other rules, citation, and quoted passage.
- **Sample address**: One of 500 multifamily properties, with street address, mailing city, state, postal code, and whatever building facts the public record included (year built, unit count, use). It has no owner name.
- **Jurisdiction stack**: The legal state, county, and city resolved for an address. It can differ from the mailing city.
- **Lookup result**: The rules that apply, cannot be decided, are superseded, are not yet effective, or are pending for one address on one date, each with an explanation and a conflict flag.
- **Change case**: One of the five supplied tests (T1 through T5), with the addresses it affects and the addresses flagged for human review.
- **Audit record**: The source, retrieval date, as-of date, and reasoning boundary for one answer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every rule in the catalog has a quoted passage of at least 20 characters that appears in the cited source, along with the source location and retrieval date. A review of the catalog finds no invented passage.
- **SC-002**: The address report contains a lookup for all 500 sample addresses as of 2026-10-01, and omits rules that do not apply.
- **SC-003**: All five change cases match the expected behavior in User Story 3, including an empty affected set for the failed Massachusetts rent-control question.
- **SC-004**: Every lookup whose coverage depends on a missing year built, unit count, certificate of occupancy, or owner type returns unknown and names that missing fact. Buildings in a certificate-of-occupancy cutoff year return unknown.
- **SC-005**: Mailing-city mismatches are resolved to the legal city. An address mailed as Van Nuys inside Los Angeles, or as a Boston neighborhood, is covered under the legal city.
- **SC-006**: Every person-facing answer shows an as-of date and states that it is not legal advice. A reader can follow any cited answer back to the source passage and the audit record without asking the original author.
- **SC-007**: Santa Ana rules appear in the catalog and on zero sample-address lookups. Berkeley's two published effective dates, Los Angeles's two published rent-formula dates, the FAIR Act preemption question, and the missing single 2026 California screening-fee figure are flagged rather than silently resolved.

## Assumptions

- This feature is the whole navigator: the rule catalog, address lookup, and the five change cases. Spanish wording, a confidence indicator, a new jurisdiction beyond the supplied corpus, and a separate audit screen are out of scope until those three parts are complete.
- The default query date is 2026-10-01. Other dates are required for the change cases and for any as-of question a reviewer asks about a rule that has an effective date.
- The corpus covers California, New Jersey, and Massachusetts, and the cities Los Angeles, San Francisco, San Diego, Berkeley, Santa Ana, Jersey City, Hoboken, Newark, Boston, and Cambridge. No other place is in scope.
- The address sample is the supplied set of about 500 properties. Counts by mailing area are Los Angeles 80, San Francisco 80, San Diego 50, Berkeley 40, Jersey City 50, Hoboken 40, Newark 50, Boston 60, and Cambridge 50.
- Plain-language explanations are in English. The required submission files are the rule catalog, the lookup report, and the change report described by the participant guide.
- Link-only sources stay unused for rule text. Official text already captured in the corpus is the text the system reads.
- Known gaps in the public records stay gaps. Owner names will not be added, and year built will not be substituted for a certificate of occupancy.
