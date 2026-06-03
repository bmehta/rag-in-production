# Contributing

Thank you for your interest in contributing to the RAG Pipeline project! This document outlines how to contribute.

## Code of Conduct

- Be respectful and inclusive
- Focus on the code, not the person
- Help others learn and grow
- Report issues constructively

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/rag-in-production.git
cd rag-in-production
```

### 2. Set Up Development Environment

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Frontend

```bash
cd frontend
npm install
```

### 3. Set Environment Variables

```bash
cp .env.example .env.local
# Edit .env.local with your API keys
```

### 4. Start Development Services

```bash
# Start OpenSearch
docker-compose up opensearch

# In another terminal, start backend
cd backend
python -m uvicorn app.main:app --reload

# In another terminal, start frontend
cd frontend
npm run dev
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-name
```

**Branch naming**:
- `feature/...` for new features
- `fix/...` for bug fixes
- `docs/...` for documentation
- `refactor/...` for code cleanup

### 2. Make Changes

- Write clean, readable code
- Follow existing code style (Black for Python, Prettier for TypeScript)
- Add docstrings/comments for complex logic
- Test your changes locally

### 3. Format & Lint

```bash
# Backend (Python)
cd backend
black app/
ruff check app/ --fix

# Frontend (TypeScript/JavaScript)
cd frontend
npm run lint --fix
```

### 4. Test Your Changes

```bash
# Backend tests
cd backend
pytest tests/

# Frontend tests
cd frontend
npm test

# Integration tests
python tests/test_pipeline.py
```

### 5. Commit & Push

```bash
git add .
git commit -m "feat: add new feature description"
git push origin feature/your-feature-name
```

**Commit message format**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Formatting (no logic change)
- `refactor:` - Code restructuring
- `perf:` - Performance improvement
- `test:` - Tests

### 6. Create a Pull Request

1. Go to GitHub and create a Pull Request
2. Describe your changes
3. Reference any related issues
4. Wait for review

## What Can You Contribute?

### 🎯 Features

- **Retrieval improvements**: Better ranking, new search methods
- **UI enhancements**: Improved interface, new pages
- **Backend optimization**: Faster ingestion, lower latency
- **Documentation**: Examples, tutorials, best practices

### 🐛 Bug Fixes

- Found a bug? Open an issue first
- Describe steps to reproduce
- Include error logs
- Submit PR with fix

### 📚 Documentation

- Improve existing docs
- Add usage examples
- Create troubleshooting guides
- Add inline code comments

### ✅ Testing

- Add unit tests
- Add integration tests
- Improve test coverage
- Test edge cases

### 🎨 Design

- UI/UX improvements
- Better visualizations
- Accessibility enhancements
- Mobile responsiveness

## Code Style Guide

### Python (Backend)

```python
"""Module docstring."""

def function_name(param: str) -> str:
    """Function docstring with type hints."""
    # Use async/await for I/O operations
    pass


class ClassName:
    """Class docstring."""
    
    async def method_name(self) -> str:
        """Method docstring."""
        pass
```

**Guidelines**:
- Use type hints everywhere
- Use async/await for I/O
- Max line length: 88 (Black default)
- Use docstrings for public APIs
- Use `structlog` for logging

### TypeScript (Frontend)

```typescript
// File header comment if needed

interface Props {
  name: string;
  age: number;
}

export default function ComponentName({ name, age }: Props) {
  // Implementation
  return <div>{name}</div>;
}
```

**Guidelines**:
- Use TypeScript (no `any` types)
- Use functional components with hooks
- Use Tailwind for styling
- Use constants for magic strings/numbers
- Export at the end of file

## Testing Guidelines

### Backend (pytest)

```python
import pytest
from app.ingest import PDFIngestionPipeline

@pytest.mark.asyncio
async def test_chunking():
    """Test that chunking produces expected output."""
    pipeline = PDFIngestionPipeline()
    chunks = await pipeline._chunk_text(
        {1: "test " * 1000},
        "test.pdf"
    )
    assert len(chunks) > 0
    assert all(len(c["text"].split()) <= 800 for c in chunks)
```

### Frontend (Jest/React Testing Library)

```typescript
import { render, screen } from '@testing-library/react';
import QueryPage from './index';

describe('QueryPage', () => {
  it('renders search input', () => {
    render(<QueryPage />);
    expect(screen.getByPlaceholderText(/ask a question/i)).toBeInTheDocument();
  });
});
```

## Documentation Style

### README & Guides

- Start with overview
- Include practical examples
- Link to detailed documentation
- Add troubleshooting section

### Inline Comments

```python
# Good: Explain WHY
# We use sliding window with 20% overlap to preserve context
# across chunk boundaries and improve retrieval quality

# Avoid: Explaining WHAT (code already shows this)
# Set overlap_ratio to 0.2
```

### API Documentation

```python
async def query_and_generate(
    query: str,
    top_k: int = 5
) -> Tuple[str, List[dict]]:
    """
    Execute hybrid search and generate an answer.
    
    Args:
        query: User query string
        top_k: Number of top results to return
    
    Returns:
        Tuple of (generated_answer, source_chunks)
        
    Raises:
        ValueError: If query is empty
        RuntimeError: If OpenSearch is unavailable
    """
    pass
```

## Pull Request Requirements

Before submitting a PR, ensure:

- [ ] Code follows style guide
- [ ] Tests pass locally (`pytest`, `npm test`)
- [ ] Linting passes (`black`, `ruff`, `eslint`)
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No merge conflicts
- [ ] Branch is up-to-date with main

## Review Process

### What We Look For

1. **Correctness**: Does the code work?
2. **Clarity**: Is it easy to understand?
3. **Testing**: Are edge cases covered?
4. **Performance**: Any regressions?
5. **Documentation**: Will others understand it?

### Responding to Feedback

- Treat feedback as suggestions, not criticism
- Ask for clarification if needed
- Make requested changes promptly
- Push changes to same branch (updates PR)
- Request re-review when done

## Reporting Issues

### Bug Reports

Include:
- Description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, versions)
- Error logs/screenshots

### Feature Requests

Include:
- Clear description of feature
- Why it's needed
- Proposed implementation (optional)
- Example use case

## Recognition

Contributors will be:
- Added to CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in relevant code

## Questions?

- Open a GitHub Discussion
- Ask in Pull Request comments
- Reach out to maintainers

## Resources

- [Architecture Documentation](./docs/ARCHITECTURE.md)
- [Chunking Strategy](./docs/CHUNKING_STRATEGY.md)
- [Scaling Roadmap](./docs/SCALING.md)
- [API Documentation](./README.md#api-endpoints)

Thank you for contributing! 🎉
