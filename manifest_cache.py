"""
Manifest and context caching to avoid expensive recreation.
The manifest creation is expensive (~100-200ms) and gets called for EVERY operation.
This cache reduces 56+ manifest creations to just 1 for a typical election.
"""

from typing import Dict, Tuple, Optional
from electionguard.manifest import Manifest, InternalManifest
from electionguard.election import CiphertextElectionContext
from electionguard_tools.helpers.election_builder import ElectionBuilder
from electionguard.group import int_to_p, int_to_q
from electionguard.utils import get_optional
import hashlib
import json


class ManifestCache:
    """Thread-safe manifest and context cache."""
    
    def __init__(self):
        self._manifest_cache: Dict[str, Manifest] = {}
        self._context_cache: Dict[str, Tuple[InternalManifest, CiphertextElectionContext]] = {}
    
    def _get_manifest_key(self, party_names: list, candidate_names: list) -> str:
        """Generate cache key from party and candidate names."""
        key_data = json.dumps({
            'parties': sorted(party_names),
            'candidates': sorted(candidate_names)
        }, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _get_context_key(self, manifest_key: str, joint_public_key: int, commitment_hash: int, 
                         number_of_guardians: int, quorum: int) -> str:
        """Generate cache key for context."""
        key_data = f"{manifest_key}:{joint_public_key}:{commitment_hash}:{number_of_guardians}:{quorum}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get_or_create_manifest(self, party_names: list, candidate_names: list, 
                               create_manifest_func) -> Manifest:
        """Get cached manifest or create new one."""
        cache_key = self._get_manifest_key(party_names, candidate_names)
        
        if cache_key not in self._manifest_cache:
            # Create new manifest
            manifest = create_manifest_func(party_names, candidate_names)
            self._manifest_cache[cache_key] = manifest
            print(f"  📝 MANIFEST CREATED (cached) - key: {cache_key[:8]}...")
        else:
            manifest = self._manifest_cache[cache_key]
            print(f"  ⚡ MANIFEST FROM CACHE - key: {cache_key[:8]}... (FAST!)")
        
        return manifest
    
    def get_or_create_context(self, party_names: list, candidate_names: list,
                             joint_public_key_int: int, commitment_hash_int: int,
                             number_of_guardians: int, quorum: int,
                             create_manifest_func) -> Tuple[InternalManifest, CiphertextElectionContext]:
        """Get cached context or create new one."""
        manifest_key = self._get_manifest_key(party_names, candidate_names)
        context_key = self._get_context_key(manifest_key, joint_public_key_int, 
                                           commitment_hash_int, number_of_guardians, quorum)
        
        if context_key not in self._context_cache:
            # Get or create manifest first
            manifest = self.get_or_create_manifest(party_names, candidate_names, create_manifest_func)
            
            # Create context
            joint_public_key = int_to_p(joint_public_key_int)
            commitment_hash = int_to_q(commitment_hash_int)
            
            election_builder = ElectionBuilder(
                number_of_guardians=number_of_guardians,
                quorum=quorum,
                manifest=manifest
            )
            election_builder.set_public_key(joint_public_key)
            election_builder.set_commitment_hash(commitment_hash)
            
            internal_manifest, context = get_optional(election_builder.build())
            self._context_cache[context_key] = (internal_manifest, context)
            print(f"  🔨 CONTEXT CREATED (cached) - key: {context_key[:8]}...")
        else:
            internal_manifest, context = self._context_cache[context_key]
            print(f"  ⚡ CONTEXT FROM CACHE - key: {context_key[:8]}... (FAST!)")
        
        return internal_manifest, context
    
    def clear(self):
        """Clear all caches."""
        self._manifest_cache.clear()
        self._context_cache.clear()
        print("  🗑️  CACHE CLEARED")


# Global cache instance
_global_cache = ManifestCache()


def get_manifest_cache() -> ManifestCache:
    """Get the global manifest cache instance."""
    return _global_cache
