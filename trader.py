import os
import sys
from pygraph.classes.graph import graph
from pygraph.readwrite.dot import write
from  pygraph.algorithms.cycles import find_cycle

sys.path.append("/Users/wojtek/Sources/btce-api/")
import btceapi

from decorators import debug
import sqlalchemy as sa


class Secrets:
    key='3VHY49XV-915CL848-ZL4GZZRW-U0IMFDLY-CHSQTXK0'
    secret='02bc45897f501efeb23c4fb0645e290175bad695536c0332ddc40da553276da1'

class KeyFileManager:
    def __init__(self, key_file_path):
        self.key_file = key_file_path
        self.handler = btceapi.KeyHandler(self.key_file, resaveOnDeletion=True)

    def get_handler(self):
        return self.handler

class Database():
    '''
    - Database should manage DB migrations and abstraction
    - Should return database object to interact with
    '''
    def __init__(self):
        self.sqlite_db_path = "trader.db"
        self.db = sa.create_engine('sqlite:///' + self.sqlite_db_path)
        self.metadata = sa.MetaData(self.db)
        self.db_migrate()

    def db_migrate(self):
        create_db = not os.path.isfile(self.sqlite_db_path)
        if create_db:
            print "Creating database"
            print "...secrets table"
            secrets = sa.Table('secrets', self.metadata,
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('slug', sa.String(20)),
                    sa.Column('value', sa.String(100))
                    )
            secrets.create()
            i = secrets.insert()
            i.execute({'slug' : 'key', 'value' : Secrets.key},
                      {'slug' : 'secret', 'value' : Secrets.secret}
                    )
            print "...currencies table"
            currencies = sa.Table('currencies', self.metadata,
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('symbol', sa.String(16)),
                    sa.Column('name', sa.String(100))
                    )
            currencies.create()
            i = currencies.insert()
            i.execute({'symbol' : 'USD', 'name' : 'United States Dollar'},
                      {'symbol' : 'BTC', 'name' : 'Bitcoin'},
                      {'symbol' : 'LTC', 'name' : 'Litecoin'},
                      {'symbol' : 'PPC', 'name' : 'Peercoin'},
                      {'symbol' : 'FTC', 'name' : 'Feathercoin'},
                      {'symbol' : 'NMC', 'name' : 'Namecoin'}
                      )
            print "...done creating tables"

    def get_db(self):
        return self.db

class CurrencyPair:
    ''' Return currency pair cost of conversion with respect to fee '''
    def __init__(self, currency_from, currency_to, cost):
        self.pair = {'from' : currency_from,
                     'to'   : currency_to,
                     'cost' : cost}
    def refresh(self):
        ''' Tell api to refresh values '''
        pass
    
    def data(self):
        return self.pair

class TradeGraph:
    ''' 
    - TradeGraph should keep the graph of currency pairs with all transition costs
    - TradeGraph should propose profitable transaction chains
        * example transaction triad : ['ltc_btc', 'btc_ftc', 'ftc_ltc']
    - TradeGraph should be initialized with dictionary of pair costs
    '''
    def __init__(self, pairs_rates):
        self.trade_fee = 0.02
        self.graph_depth = 5 
        self.pairs_rates = pairs_rates
        self.graph = graph()
        self.trade_graph = self.init_graph()
        self.path = self.paths_from_to(self.graph, "nvc", "trc")  
        print "Paths: %s"  % str(self.path)                                       
    
    def __repr__(self):
        return self.graph
        
    def init_graph(self):
        ''' Returns graph where nodes are currencies and edges are exchange rates'''
        self.add_nodes()
        self.add_edges()
        self.add_edges_attributes()
        self.draw_graph()
    
    def draw_graph(self):
        dot = write(self.graph)
        f = open('currencies.dot', 'a')
        f.write(dot)
        f.close()
        command = '/usr/local/bin/dot -Tpng currencies.dot > currencies.png'
        print "Generating graph with %s" % command
        os.system(command)
        
        
    def add_nodes(self):
        ''' adds nodes to trade graph '''
        try:
            self.graph.add_nodes(list(btceapi.all_currencies))
            return True
        except Exception, e:
            print "Could not add nodes to tradegraph: %s" % e
            raise
            
    def all_edges(self):
        ''' returns tuples of currency pairs '''
        return [tuple(i.split('_')) for i in btceapi.all_pairs]

    def add_edges(self):
        ''' Adds edges to trade graph '''
        try:
            for edge in self.all_edges():
                self.graph.add_edge(edge)
            return True
        except Exception, e:
            print "Could not add edges to trade graph: %s" % e
            raise

    def add_edges_attributes(self):
        ''' Ads attributes to trade graph '''
        try:
            for rate in self.pairs_rates:
                edge = tuple(rate[0].split("_"))
                edge_attribute_1 = tuple([edge[0], rate[1]])
                edge_attribute_2 = tuple([edge[1], 1/rate[1]])
                self.graph.add_edge_attribute(edge,(edge_attribute_1))
                self.graph.add_edge_attribute(edge,(edge_attribute_2))
                self.graph.add_edge_attribute(edge,("label",rate[1]))
        except Exception, e:
            print "Could not add attributes to edges: %s" % e
            raise
    
    def refresh_graph(self):
        ''' Iterate through thru all CurrencyPairs and refresh pair cost'''
        pass
    
    def get_graph(self):
        return self.graph
    
    def adjlist_find_paths(self, a, n, m, path=[]):
        '''Find paths from node index n to m using adjacency list a.'''
        path = path + [n]
        if n == m:
            return [path]
        paths = []
        for child in a[n]:
            if child not in path:
                child_paths = self.adjlist_find_paths(a, child, m, path)
                for child_path in child_paths:
                    paths.append(child_path)
        return paths

    def paths_from_to(self, graph, source, dest):
        '''Find paths in graph from vertex source to vertex dest.'''
        a = graph.node_neighbors
        n = source
        m = dest
        return self.adjlist_find_paths(a, n, m)
    
    def find_all_flows(self):
        pass  
    
    def find_cycle_to_ancestor(self, spanning_tree, node, ancestor):
        """
        Find a cycle containing both node and ancestor.
        """
        path = []
        while (node != ancestor):
            if node is None:
                return []
            path.append(node)
            node = spanning_tree[node]
        path.append(node)
        path.reverse()
        return path
    
    def find_all_cycles(self):
        """
        Find all cycles in the given graph.
    
        This function will return a list of lists of nodes, which form cycles in the
        graph or an empty list if no cycle exists.
        """
    
        def dfs(node):
            """
            Depth-first search subfunction.
            """
            visited.add(node)
            # Explore recursively the connected component
            for each in self.graph[node]:
                if each not in visited:
                    spanning_tree[each] = node
                    dfs(each)
                else:
                    if (spanning_tree[node] != each):
                        cycle = self.find_cycle_to_ancestor(spanning_tree, node, each)
                        if cycle:
                            cycles.append(cycle)
    
        visited = set()         # List for marking visited and non-visited nodes
        spanning_tree = {}      # Spanning tree
        cycles = []
    
        # Algorithm outer-loop
        for each in self.graph:
            # Select a non-visited node
            if each not in visited:
                spanning_tree[each] = None
                # Explore node's connected component
                dfs(each)

        return cycles

    
class MarketKnowledge:
    '''
    - Knowledge should be able to access database but leave
    all the lower level logic to Database class
    - Knowledge should provide API abstraction
    '''
    def __init__(self, key_file_path):
        self.handler = KeyFileManager(key_file_path).get_handler()
        self.db = self.init_database()
        self.trade_api = self.init_trade_api()
        self.all_currencies = btceapi.all_currencies
        self.pairs_rates = self.init_pairs_rates()
        self.graph = TradeGraph(self.pairs_rates).get_graph()
        self.all_cycles = TradeGraph(self.pairs_rates).find_all_cycles()
        
    def __repr__(self):
        return str(self.handler)
    
    @debug
    def init_pairs_rates(self):
        ''' Returns list of tuples containing (pair <string>, rate <float>)'''
        try:
            pairs_rates = []
            for pair in btceapi.all_pairs:
                rate = btceapi.getTicker(pair).avg
                pairs_rates.append((pair, rate))
            return pairs_rates
        except Exception, e:
            print "Could not produce pairs rates: %s" % e
            raise
    
    def init_database(self):
        db = Database().get_db()
        return db

    def init_trade_api(self):
        try:
            self.api_connection = btceapi.BTCEConnection()
            self.key = self.handler.getKeys()[0]
            trade_api = btceapi.TradeAPI(self.key, self.handler)
            return trade_api
        except Exception, e:
            print "Could not initialize API because %s" % e
            raise
    
    @debug
    def get_pair_depth(self, pair):
        ''' Returns asks and bids '''
        asks, bids = btceapi.getDepth(pair)
        ask_prices, ask_volumes = zip(*asks)
        bid_prices, bid_volumes = zip(*bids)
        pair_depth = {pair: {'ask_prices': ask_prices,
                             'ask_volumes': ask_volumes,
                             'bid_prices': bid_prices, 
                             'bid_volumes' : bid_volumes
                             }
                      }
        return pair_depth
    
    def get_all_depth(self):
        all_pairs_depth = {}
        for pair in btceapi.all_pairs:
            pair_depth = self.get_pair_depth(pair)
            all_pairs_depth[pair] = pair_depth
        return all_pairs_depth

    def get_ticker(self, pair):
        ''' Returns high, low, avg, etc '''
        pass

    def get_trade_fee(self, pair):
        ''' Returns exchange's trade fee '''
        pass

    def get_info(self):
        ''' Returns dictionary that contains all needed data '''
        r = self.trade_api.getInfo(connection = self.api_connection)
        balances = self.get_balances(r)
        open_orders = self.get_open_orders()
        transaction_history_count = self.get_transaction_history_count(r)
        market_depth = self.get_all_depth()
        info = {'balances' : balances,
                'open_orders' : open_orders,
                'transaction_history_count' : transaction_history_count,
                'market_depth' : market_depth
                }
        return info

    def get_transaction_history_count(self, r):
        return r.transaction_count


    def get_open_orders(self):
        orders = self.trade_api.activeOrders(connection = self.api_connection)
        orders_list = {}
        for o in orders:
            order = {}
            order['id'] = o.order_id
            order['type'] = o.type
            order['pair'] = o.pair
            order['rate'] = o.rate
            order['amount'] = o.amount
            order['timestamp_created'] = o.timestamp_created
            order['status'] = o.status
            orders_list[o.order_id] = order
        return orders_list

    def get_balances(self, r):
        balances = {}
        for currency in self.all_currencies:
            balance = getattr(r, "balance_" + currency)
            balances[currency.upper()] = balance
        return balances
    
    def get_graph(self):
        return self.graph
    
    def get_cycles(self):
        return self.all_cycles
    

    
class Trader():
    '''
    - Trader should receive currencies to trade with from database
    - Trader should compute transition costs/profits so trader must know:
        * current commission/fee of exchange api
        * last transactions (good to have)
        * price of every cryptocurrency with respect to dollar
        * trader should keep trace of all operations
    - Trader should perform only synchronous trades (live trading)
    - Trader should have some fallback-currency or safety strategy
    '''
    def __init__(self, key_file):
        self.market = MarketKnowledge(key_file)
        self.graph = self.market.get_graph()
        self.cycles = self.market.get_cycles()
        #self.trade_pairs =  TradeGraph().trade_pairs

    def trade(self):
        print "Graph"
        print self.graph
        print "Cycles"
        print self.cycles
        #pass

if __name__ == "__main__":
    if len(sys.argv) > 0:
        print "Launching trader with key file %s" % sys.argv[1]
        t = Trader(sys.argv[1])
        t.trade()
