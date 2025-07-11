"""
Priority Queue Manager
Manages request queuing with priority and persistence
"""

import asyncio
import heapq
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pickle
import aiofiles
import os
from collections import defaultdict
import logging

from .exceptions import QueueError


@dataclass(order=True)
class QueueItem:
    """Priority queue item"""
    priority: int
    timestamp: float = field(compare=False)
    data: Dict[str, Any] = field(compare=False)
    item_id: str = field(compare=False)


class QueueManager:
    """
    Advanced queue manager with:
    - Priority-based ordering
    - Persistence support
    - Queue statistics
    - Dead letter queue
    - Queue partitioning
    - Rate limiting per partition
    """

    def __init__(self, max_size: int = 1000, persist_path: Optional[str] = None):
        self.max_size = max_size
        self.persist_path = persist_path
        self.logger = logging.getLogger(__name__)
        
        # Main priority queue
        self._queue: List[QueueItem] = []
        self._queue_lock = asyncio.Lock()
        
        # Dead letter queue for failed items
        self._dlq: List[Tuple[Dict[str, Any], str, datetime]] = []
        self._dlq_max_size = 100
        
        # Partitioned queues for different request types
        self._partitions: Dict[str, List[QueueItem]] = defaultdict(list)
        self._partition_limits: Dict[str, int] = {}
        
        # Statistics
        self._stats = {
            "total_enqueued": 0,
            "total_dequeued": 0,
            "total_failed": 0,
            "total_expired": 0,
            "partition_counts": defaultdict(int)
        }
        
        # Item tracking
        self._item_map: Dict[str, QueueItem] = {}
        self._processing: Dict[str, datetime] = {}
        
        # Load persisted queue if path provided
        if self.persist_path:
            asyncio.create_task(self._load_queue())

    async def add(self, item: Dict[str, Any], priority: Any, partition: Optional[str] = None):
        """Add item to queue with priority"""
        async with self._queue_lock:
            # Check queue size
            if len(self._queue) >= self.max_size:
                # Try to remove expired items first
                await self._cleanup_expired()
                
                if len(self._queue) >= self.max_size:
                    raise QueueError("Queue is full")
            
            # Create queue item
            queue_item = QueueItem(
                priority=priority.value if hasattr(priority, "value") else priority,
                timestamp=time.time(),
                data=item,
                item_id=item.get("id", str(time.time()))
            )
            
            # Add to appropriate queue
            if partition:
                # Check partition limit
                if partition in self._partition_limits:
                    partition_items = len([i for i in self._queue if i.data.get("partition") == partition])
                    if partition_items >= self._partition_limits[partition]:
                        raise QueueError(f"Partition {partition} is full")
                
                item["partition"] = partition
                self._partitions[partition].append(queue_item)
                heapq.heappush(self._partitions[partition], queue_item)
                self._stats["partition_counts"][partition] += 1
            
            # Add to main queue
            heapq.heappush(self._queue, queue_item)
            self._item_map[queue_item.item_id] = queue_item
            self._stats["total_enqueued"] += 1
            
            # Persist if enabled
            if self.persist_path:
                await self._persist_queue()

    async def get(self, partition: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get highest priority item from queue"""
        async with self._queue_lock:
            queue_to_use = self._queue
            
            # Use partition queue if specified
            if partition and partition in self._partitions:
                queue_to_use = self._partitions[partition]
            
            while queue_to_use:
                queue_item = heapq.heappop(queue_to_use)
                
                # Check if item is expired (older than 1 hour)
                if time.time() - queue_item.timestamp > 3600:
                    self._stats["total_expired"] += 1
                    if queue_item.item_id in self._item_map:
                        del self._item_map[queue_item.item_id]
                    continue
                
                # Also remove from main queue if using partition
                if partition and queue_to_use != self._queue:
                    self._queue = [item for item in self._queue if item.item_id != queue_item.item_id]
                    heapq.heapify(self._queue)
                
                # Track processing
                self._processing[queue_item.item_id] = datetime.utcnow()
                
                # Update stats
                self._stats["total_dequeued"] += 1
                if partition:
                    self._stats["partition_counts"][partition] -= 1
                
                # Remove from item map
                if queue_item.item_id in self._item_map:
                    del self._item_map[queue_item.item_id]
                
                # Persist if enabled
                if self.persist_path:
                    await self._persist_queue()
                
                return queue_item.data
            
            return None

    async def peek(self, n: int = 1) -> List[Dict[str, Any]]:
        """Peek at top n items without removing them"""
        async with self._queue_lock:
            # Get n smallest items
            items = heapq.nsmallest(n, self._queue)
            return [item.data for item in items]

    async def remove(self, item_id: str) -> bool:
        """Remove specific item from queue"""
        async with self._queue_lock:
            if item_id not in self._item_map:
                return False
            
            # Remove from queue
            self._queue = [item for item in self._queue if item.item_id != item_id]
            heapq.heapify(self._queue)
            
            # Remove from partitions
            queue_item = self._item_map[item_id]
            partition = queue_item.data.get("partition")
            if partition and partition in self._partitions:
                self._partitions[partition] = [
                    item for item in self._partitions[partition]
                    if item.item_id != item_id
                ]
                heapq.heapify(self._partitions[partition])
            
            # Remove from tracking
            del self._item_map[item_id]
            if item_id in self._processing:
                del self._processing[item_id]
            
            return True

    async def requeue(self, item: Dict[str, Any], reason: str = "retry"):
        """Requeue an item that failed processing"""
        item_id = item.get("id")
        
        # Remove from processing
        if item_id in self._processing:
            del self._processing[item_id]
        
        # Increment retry count
        if "retry_count" not in item:
            item["retry_count"] = 0
        item["retry_count"] += 1
        
        # Move to DLQ if too many retries
        if item["retry_count"] > 3:
            await self.add_to_dlq(item, f"Max retries exceeded: {reason}")
            return
        
        # Re-add with lower priority
        original_priority = item.get("priority", 3)
        new_priority = min(original_priority + 1, 4)  # Lower priority for retries
        
        await self.add(item, new_priority)

    async def add_to_dlq(self, item: Dict[str, Any], reason: str):
        """Add item to dead letter queue"""
        async with self._queue_lock:
            # Maintain DLQ size limit
            if len(self._dlq) >= self._dlq_max_size:
                self._dlq.pop(0)  # Remove oldest
            
            self._dlq.append((item, reason, datetime.utcnow()))
            self._stats["total_failed"] += 1
            
            self.logger.warning(f"Item {item.get('id')} moved to DLQ: {reason}")

    async def get_dlq_items(self) -> List[Tuple[Dict[str, Any], str, datetime]]:
        """Get all items from dead letter queue"""
        async with self._queue_lock:
            return self._dlq.copy()

    async def replay_dlq_item(self, index: int) -> bool:
        """Replay an item from DLQ"""
        async with self._queue_lock:
            if 0 <= index < len(self._dlq):
                item, _, _ = self._dlq.pop(index)
                item["retry_count"] = 0  # Reset retry count
                await self.add(item, 3)  # Normal priority
                return True
            return False

    def size(self) -> int:
        """Get current queue size"""
        return len(self._queue)

    def partition_size(self, partition: str) -> int:
        """Get size of specific partition"""
        return len(self._partitions.get(partition, []))

    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        async with self._queue_lock:
            # Calculate processing times
            processing_items = []
            for item_id, start_time in self._processing.items():
                duration = (datetime.utcnow() - start_time).total_seconds()
                processing_items.append({
                    "id": item_id,
                    "duration": duration
                })
            
            return {
                **self._stats,
                "current_size": len(self._queue),
                "dlq_size": len(self._dlq),
                "processing_count": len(self._processing),
                "processing_items": processing_items,
                "partitions": {
                    name: len(items) for name, items in self._partitions.items()
                },
                "oldest_item_age": self._get_oldest_item_age()
            }

    def _get_oldest_item_age(self) -> Optional[float]:
        """Get age of oldest item in queue"""
        if not self._queue:
            return None
        
        oldest = min(self._queue, key=lambda x: x.timestamp)
        return time.time() - oldest.timestamp

    async def _cleanup_expired(self):
        """Remove expired items from queue"""
        current_time = time.time()
        expired_ids = []
        
        for item in self._queue:
            if current_time - item.timestamp > 3600:  # 1 hour expiry
                expired_ids.append(item.item_id)
                self._stats["total_expired"] += 1
        
        # Remove expired items
        for item_id in expired_ids:
            await self.remove(item_id)

    async def clear(self):
        """Clear all items from queue"""
        async with self._queue_lock:
            self._queue.clear()
            self._partitions.clear()
            self._item_map.clear()
            self._processing.clear()
            
            if self.persist_path:
                await self._persist_queue()

    async def set_partition_limit(self, partition: str, limit: int):
        """Set maximum items for a partition"""
        self._partition_limits[partition] = limit

    async def _persist_queue(self):
        """Persist queue to disk"""
        if not self.persist_path:
            return
        
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            
            # Serialize queue data
            data = {
                "queue": [(item.priority, item.timestamp, item.data, item.item_id) 
                         for item in self._queue],
                "dlq": self._dlq,
                "stats": self._stats,
                "partitions": {
                    name: [(item.priority, item.timestamp, item.data, item.item_id) 
                          for item in items]
                    for name, items in self._partitions.items()
                }
            }
            
            # Write to temporary file first
            temp_path = f"{self.persist_path}.tmp"
            async with aiofiles.open(temp_path, "wb") as f:
                await f.write(pickle.dumps(data))
            
            # Rename to final path
            os.replace(temp_path, self.persist_path)
            
        except Exception as e:
            self.logger.error(f"Failed to persist queue: {e}")

    async def _load_queue(self):
        """Load queue from disk"""
        if not self.persist_path or not os.path.exists(self.persist_path):
            return
        
        try:
            async with aiofiles.open(self.persist_path, "rb") as f:
                data = pickle.loads(await f.read())
            
            # Restore queue
            self._queue = [
                QueueItem(priority=p, timestamp=t, data=d, item_id=i)
                for p, t, d, i in data.get("queue", [])
            ]
            heapq.heapify(self._queue)
            
            # Restore other data
            self._dlq = data.get("dlq", [])
            self._stats = data.get("stats", self._stats)
            
            # Restore partitions
            for name, items in data.get("partitions", {}).items():
                self._partitions[name] = [
                    QueueItem(priority=p, timestamp=t, data=d, item_id=i)
                    for p, t, d, i in items
                ]
                heapq.heapify(self._partitions[name])
            
            # Rebuild item map
            for item in self._queue:
                self._item_map[item.item_id] = item
            
            self.logger.info(f"Loaded {len(self._queue)} items from persistent storage")
            
        except Exception as e:
            self.logger.error(f"Failed to load queue: {e}")

    async def export_metrics(self) -> Dict[str, Any]:
        """Export detailed metrics for monitoring"""
        async with self._queue_lock:
            # Priority distribution
            priority_dist = defaultdict(int)
            age_dist = {"<1m": 0, "1-5m": 0, "5-30m": 0, ">30m": 0}
            
            current_time = time.time()
            
            for item in self._queue:
                priority_dist[item.priority] += 1
                
                age = current_time - item.timestamp
                if age < 60:
                    age_dist["<1m"] += 1
                elif age < 300:
                    age_dist["1-5m"] += 1
                elif age < 1800:
                    age_dist["5-30m"] += 1
                else:
                    age_dist[">30m"] += 1
            
            return {
                "queue_metrics": {
                    "size": len(self._queue),
                    "capacity_used": len(self._queue) / self.max_size,
                    "priority_distribution": dict(priority_dist),
                    "age_distribution": age_dist,
                    "dlq_size": len(self._dlq),
                    "processing_count": len(self._processing)
                },
                "throughput_metrics": {
                    "total_enqueued": self._stats["total_enqueued"],
                    "total_dequeued": self._stats["total_dequeued"],
                    "total_failed": self._stats["total_failed"],
                    "total_expired": self._stats["total_expired"]
                },
                "partition_metrics": {
                    name: {
                        "size": len(items),
                        "limit": self._partition_limits.get(name, "unlimited"),
                        "total_processed": self._stats["partition_counts"][name]
                    }
                    for name, items in self._partitions.items()
                }
            }