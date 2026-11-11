# Verity — Product

## What it is
Verity is an autonomous agent that researches tokens using live RYO-CHAN tools, publishes a structured practice receipt for each decision, and later grades that receipt against real price movement. The graded receipts are public.

## What users do
- Open the public page.
- Read the agent’s latest practice receipts.
- Open a receipt to see the evidence chain and reasoning.
- Return later to check the grade (correct, incorrect, or still pending).
- Share a receipt link.

No account is required to view. No chat. No real trading.

## Core loop
1. Select a token or short list of tokens.
2. Call multiple RYO-CHAN research tools.
3. Write a practice receipt.
4. Grade the receipt after a defined window.
5. Publish the receipt and grade.

## Receipt contents
Every receipt must include:
- token symbol
- timestamp
- tools called and their status
- evidence summary
- thesis
- practice action (long / short / watch / avoid)
- invalidation level
- confidence
- grade (pending / correct / incorrect) once available
- grade timestamp

## Tracks served
- Autonomous Agents: the agent runs the loop autonomously.
- New Skills: the receipt + grade logic is exposed as a callable skill.

## Out of scope
- Real order placement
- Multi-user chat or rooms
- Account system for viewing
- Complex multi-page dashboards
