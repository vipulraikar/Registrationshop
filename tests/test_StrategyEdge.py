import unittest
import os
import shutil

from core.StrategyEdge import StrategyEdge
from core.StrategyNode import StrategyNode
from core.Transformation import Transformation


class StrategyEdgeTest(unittest.TestCase):

	# Setup and teardown

	def setUp(self):
		self.edge = StrategyEdge()

	def tearDown(self):
		del self.edge

	def testStrategyEdge(self):
		self.assertIsNotNone(self.edge)
		self.assertTrue(hasattr(self.edge, "parentNode"))
		self.assertTrue(hasattr(self.edge, "childNode"))
		self.assertTrue(hasattr(self.edge, "transformation"))

	def testExecutingStrategyEdge(self):
		# Load simple transformation from disk
		transformation = Transformation()
		path = os.path.dirname(os.path.abspath(__file__))
		transformation.loadFromFile(unicode(path) + "/data/Sample.txt")

		# Create a parent node with pointers to the input datasets
		parentNode = StrategyNode()
		parentNode.dataset = path + "/data/hi-3.mhd"
		parentNode.fixedData = path + "/data/hi-5.mhd"
		parentNode.outputFolder = path + "/data/data"

		# Create a child node that points to the output folder
		childNode = StrategyNode()
		childNode.dirty = True
		childNode.outputFolder = path + "/data/data/data"

		# Connect the edge to the transformation and the two nodes
		self.edge.parentNode = parentNode
		self.edge.childNode = childNode
		self.edge.transformation = transformation

		self.assertTrue(self.edge.childNode.dirty)
		self.assertIsNone(self.edge.childNode.dataset)

		self.edge.execute() # TODO: make it execute Elastix

		self.assertFalse(self.edge.childNode.dirty)
		self.assertIsNotNone(self.edge.childNode.dataset)
		self.assertTrue(os.path.exists(self.edge.childNode.dataset))

		# Cleanup test directory
		try:
			if os.path.exists(path + "/data/data"):
				shutil.rmtree(path + "/data/data")
		except Exception, e:
			raise e