---
name: karpathy-guidelines
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria.
license: MIT
---

# Karpathy Guidelines

Forked from [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) (MIT).

## When to use
- 새 코드 작성, 리팩터링, 코드 리뷰 전.
- 다단계 구현을 시작하기 직전.

## Four core principles

### 1. Think Before Coding
State your assumptions explicitly. If uncertain, ask. 불확실함을 먼저 꺼내고, 조용히 결정하지 말 것 — 특히 되돌리기 어려운 변경 전에.

### 2. Simplicity First
Minimum code that solves the problem. Nothing speculative. 요청하지 않은 기능, 필요 없는 추상화, 조기 일반화 금지.

### 3. Surgical Changes
Touch only what you must. Clean up only your own mess. 기존 코드를 고칠 때 요청한 부분에만 집중 — 무관한 섹션 리팩터링 금지, 이미 있는 죽은 코드 삭제 금지.

### 4. Goal-Driven Execution
Define success criteria. Loop until verified. 요구를 테스트 가능한 성공 기준으로 번역 후 구현. 구현 중 기준을 자주 점검.

## 이 레포에서의 실천
- 자동매매 루프(`engine/app/engine/runner.py`)를 건드릴 땐 `KIS_IS_VIRTUAL=true` 를 반드시 확인하고 수정 이유를 커밋 메시지에 명시.
- HANRIVER skill 체인에서 LLM 호출이 늘어나면 비용이 늘어남 — 필요할 때만 `claude_client.complete` 호출.
- UI 변경은 기존 `MacWindow` 컴포넌트 재사용. 새 디자인 토큰 도입 금지 (Simplicity First).
