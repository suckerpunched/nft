from multiprocessing import Pool
from itertools import product
from random import random

from pathlib import Path as path
from shutil import make_archive, rmtree

from PIL import Image
from tqdm import tqdm

class NFT :
    def __build_nft_components(self, config):
        # compile all combinations of variable components
        variable_components = [[ (f'variable.{i}', config['variable'][i][x]) for x in config['variable'][i].keys() ] for i in config['variable']]
        variable_components = list(product(*variable_components))
        
        # compile static components into single tuple
        static_components = tuple([(f'static.{i}', config['static'][i]) for i in config['static']])

        # build data tuple for each nft
        nft_collection,nft_index = [],1
        for nft in variable_components:
            unique_index = str(nft_index)
        
            # add static components
            nft = nft + static_components

            for opt in config['optional']:
                # generate random number for rarity
                random_n = random()
                choice = None

                # check if random_n passes rarity requirement for variation of an optional component
                for variation in config['optional'][opt]['variations']:
                    if random_n <= float(variation):
                        choice = tuple([( f'optional.{opt}', config['optional'][opt]['variations'][variation]['data'] )])
                        unique_index = unique_index + config['optional'][opt]['variations'][variation]['suffix']
                        nft = nft + choice
                        break

                # add static components for optional components that passes rarity requirement
                if choice:
                    static_optional = config['optional'][opt].get('static')
                    if static_optional:
                        for static_component in static_optional:
                            nft = nft + tuple([(f'optional.{static_component}', config['optional'][opt]['static'][static_component])])

            # add unique_index to drop's tuple
            nft = nft + tuple([(f'unique_index', unique_index)])
            nft_collection.append(nft)

            nft_index += 1
        
        return nft_collection

    def __unique_index(self, nft):
        # get unique_index for nft
        for component in nft:
            _type,_value = component
            if _type == 'unique_index': return _value
        raise Exception(f'unique index not found! {nft}')

    def __set_design(self, design, nft):
        # reorder layers into specified design
        new_design = []
        for design_layer in design:

            for nft_layer in nft:
                nft_layer, nft_data = nft_layer

                if design_layer == nft_layer:
                    new_design.append(nft_data)
        return (self.__unique_index(nft), new_design)

    def build_nft(self, nft):
        # build single nft and save it
        unique_index,nft = nft
        generated_nft = None

        for layer in nft:
            if generated_nft is None: generated_nft = Image.open(layer)
            else:
                layer = Image.open(layer)
                generated_nft.paste(layer, (0, 0), layer)
        
        name = self.__name_format.format(unique_index)
        generated_nft.save(f'collection/{name}.png')

    def __call__(self, config, delete_after_compression, pool_size, silent):
        # build nft components and set the design
        nft_collection = self.__build_nft_components(config['build_config'])
        nft_collection = [ self.__set_design(config['design'], nft) for nft in nft_collection ]

        # set name format for created files
        self.__name_format = config['name_format']

        if __name__ == '__main__':
            # create collection directory
            path('collection/').mkdir(exist_ok=True)

            # start pool and create collection
            with Pool(processes=pool_size) as pool: 
                if silent: pool.map(self.build_nft, nft_collection)
                else: [_ for _ in tqdm(pool.imap_unordered(self.build_nft, nft_collection), total=len(nft_collection))]
            
            # zip collection and clean up
            make_archive('collection', 'zip', 'collection')
            if delete_after_compression: rmtree('collection')
            print('done!')

if __name__ == '__main__':
    nft = NFT()

    from argparse import ArgumentParser
    from json import load

    parser = ArgumentParser(description='build nft collection')

    parser.add_argument('config', help='path to configuration file.')

    parser.add_argument('-s', '--silent', default=False, action='store_true', help='set to disable progress bar.')
    parser.add_argument('-d', '--delete_after_compression', default=True,  action='store_false', help='delete collection directory after being compressed.')
    parser.add_argument('-p', '--pool_size', type=int, default=4, help='set size of multiprocessing pool.')

    args = parser.parse_args()

    config = load(open(args.config, 'r'))
    nft(config, args.delete_after_compression, args.pool_size, args.silent)