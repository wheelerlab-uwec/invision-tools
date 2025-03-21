import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
import os
import yaml
import argparse
from typing import List, Tuple, Optional, Dict, Any


def split_by_wells(
    df, h_lines, v_lines, outer_bounds=None, h_slope=0, v_slope=float("inf")
):
    """
    Split a particle tracking dataframe into separate dataframes for each well
    based on horizontal and vertical grid lines.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame containing particle tracking data
    h_lines : list of float
        Y-intercepts of horizontal lines separating wells (internal grid lines)
    v_lines : list of float
        X-intercepts of vertical lines separating wells (internal grid lines)
    outer_bounds : tuple, optional
        Tuple of (min_x, max_x, min_y, max_y) defining the outer boundaries of the grid.
        Points outside these boundaries will be removed.
    h_slope : float, default=0
        Slope of "horizontal" lines
    v_slope : float, default=float('inf')
        Slope of "vertical" lines

    Returns:
    --------
    dict: Dictionary of DataFrames, where keys are tuples (row, col) and values are
          the corresponding DataFrames for that well
    """
    # Make a copy of the dataframe to avoid modifying the original
    working_df = df.copy()

    # Filter points based on outer boundaries if provided
    if outer_bounds is not None:
        min_x, max_x, min_y, max_y = outer_bounds

        if np.isinf(v_slope):
            # Standard case with vertical lines
            x_filter = (working_df["x"] >= min_x) & (working_df["x"] <= max_x)
        else:
            # Sloped "vertical" lines
            x_filter = (
                (working_df["x"] - (1 / v_slope) * working_df["y"]) >= min_x
            ) & ((working_df["x"] - (1 / v_slope) * working_df["y"]) <= max_x)

        # For horizontal lines
        y_filter = ((working_df["y"] - h_slope * working_df["x"]) >= min_y) & (
            (working_df["y"] - h_slope * working_df["x"]) <= max_y
        )

        # Apply both filters
        working_df = working_df[x_filter & y_filter]

        print(f"Filtered to {len(working_df)} points within outer boundaries.")

    # Sort the lines
    h_lines = sorted(h_lines)
    v_lines = sorted(v_lines)

    # Function to determine which cell a point belongs to
    def get_cell(x, y):
        # For horizontal lines (y = mx + b), we're checking y - mx > b
        row = 0
        for h_line in h_lines:
            if y - h_slope * x > h_line:
                row += 1
            else:
                break

        # For vertical lines (x = my + b), we're checking x - my > b
        # If v_slope is infinite, this simplifies to checking x > b
        col = 0
        if np.isinf(v_slope):
            for v_line in v_lines:
                if x > v_line:
                    col += 1
                else:
                    break
        else:
            # For non-vertical "vertical" lines
            for v_line in v_lines:
                if x - (1 / v_slope) * y > v_line:
                    col += 1
                else:
                    break

        return (row, col)

    # Apply the function to each point to determine its cell
    working_df["cell"] = working_df.apply(
        lambda row: get_cell(row["x"], row["y"]), axis=1
    )

    # Get unique cells
    unique_cells = working_df["cell"].unique()

    # Split the dataframe by cell
    well_dfs = {}
    for cell in unique_cells:
        well_dfs[cell] = (
            working_df[working_df["cell"] == cell].copy().drop(columns=["cell"])
        )

    print(f"Split data into {len(well_dfs)} wells")
    return well_dfs


def visualize_wells(
    df,
    well_dfs,
    h_lines=None,
    v_lines=None,
    outer_bounds=None,
    h_slope=0,
    v_slope=float("inf"),
    sample_frame=None,  # Changed default to None
    output_path=None,
):
    """
    Visualize how data is split into wells.

    Parameters:
    -----------
    df : pandas.DataFrame
        Original DataFrame containing particle tracking data
    well_dfs : dict
        Dictionary of well DataFrames returned by split_by_wells
    h_lines, v_lines, outer_bounds, h_slope, v_slope:
        Same parameters used in split_by_wells
    sample_frame : int, optional
        Which frame to visualize (to reduce clutter). If None, will plot all frames.
    output_path : str, optional
        Path where visualization should be saved. If None, will use "{input_path}_well_visualization.png"
    """
    plt.figure(figsize=(15, 10))

    # Plot all data points in light gray with transparency
    if sample_frame is not None:
        sample_df = df[df["frame"] == sample_frame]
    else:
        # Use all points but with higher transparency
        sample_df = df
    # Increased alpha for better visibility when plotting all points
    plt.scatter(sample_df["x"], sample_df["y"], c="lightgray", alpha=0.1, s=1)

    # Function to plot a sloped line
    def plot_sloped_line(
        intercept,
        slope,
        is_horizontal,
        min_x,
        max_x,
        min_y,
        max_y,
        style="k-",
        alpha=0.5,
    ):
        if is_horizontal:
            # For "horizontal" lines (y = mx + b)
            x_vals = np.linspace(min_x, max_x, 100)
            y_vals = slope * x_vals + intercept
            plt.plot(x_vals, y_vals, style, alpha=alpha)
        else:
            # For "vertical" lines (x = my + b)
            if np.isinf(slope):
                plt.axvline(x=intercept, color="k", alpha=alpha)
            else:
                y_vals = np.linspace(min_y, max_y, 100)
                x_vals = (1 / slope) * y_vals + intercept
                plt.plot(x_vals, y_vals, style, alpha=alpha)

    # Determine plot limits
    if outer_bounds:
        min_x, max_x, min_y, max_y = outer_bounds
    else:
        min_x, max_x = df["x"].min(), df["x"].max()
        min_y, max_y = df["y"].min(), df["y"].max()
        # Add some padding
        x_range = max_x - min_x
        y_range = max_y - min_y
        min_x -= x_range * 0.05
        max_x += x_range * 0.05
        min_y -= y_range * 0.05
        max_y += y_range * 0.05

    # Plot outer bounds if provided
    if outer_bounds:
        # Plot as red dashed lines
        plot_sloped_line(min_y, h_slope, True, min_x, max_x, min_y, max_y, "r--", 0.7)
        plot_sloped_line(max_y, h_slope, True, min_x, max_x, min_y, max_y, "r--", 0.7)
        plot_sloped_line(min_x, v_slope, False, min_x, max_x, min_y, max_y, "r--", 0.7)
        plot_sloped_line(max_x, v_slope, False, min_x, max_x, min_y, max_y, "r--", 0.7)

    # Plot grid lines
    if h_lines:
        for h in h_lines:
            plot_sloped_line(h, h_slope, True, min_x, max_x, min_y, max_y)
    if v_lines:
        for v in v_lines:
            plot_sloped_line(v, v_slope, False, min_x, max_x, min_y, max_y)

    # Plot individual wells with different colors
    colors = [
        "red",
        "blue",
        "green",
        "purple",
        "orange",
        "cyan",
        "magenta",
        "brown",
        "pink",
        "olive",
    ]

    # Plot individual wells with different colors and increased transparency
    for i, (cell, well_df) in enumerate(well_dfs.items()):
        color = colors[i % len(colors)]
        if sample_frame is not None:
            sample = well_df[well_df["frame"] == sample_frame]
        else:
            # Use all points but with transparency
            sample = well_df
        # Smaller point size and increased transparency when plotting all points
        plt.scatter(
            sample["x"], sample["y"], color=color, s=3, alpha=0.3, label=f"Well {cell}"
        )

    # Set up plot labels and limits
    plt.title("Particles Split by Wells")
    plt.xlabel("X Position")
    plt.ylabel("Y Position")
    plt.xlim(min_x, max_x)
    plt.ylim(min_y, max_y)

    # Set x and y ticks every 250 units
    x_ticks = np.arange(
        np.floor(min_x / 250) * 250, np.ceil(max_x / 250) * 250 + 1, 250
    )
    y_ticks = np.arange(
        np.floor(min_y / 250) * 250, np.ceil(max_y / 250) * 250 + 1, 250
    )
    plt.xticks(x_ticks)
    plt.yticks(y_ticks)

    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(False)
    plt.tight_layout()

    # Use the provided output path or generate default
    if output_path is None:
        output_path = "well_visualization.png"

    # Save the visualization
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Visualization saved to: {output_path}")


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the configuration from YAML file."""
    validated = {}

    # Validate input_path
    if "input_path" not in config:
        raise ValueError("input_path is required in the config file")
    if not isinstance(config["input_path"], str):
        raise TypeError("input_path must be a string")
    if not os.path.exists(config["input_path"]):
        raise FileNotFoundError(f"Input file not found: {config['input_path']}")
    validated["input_path"] = config["input_path"]

    # Validate output_path (optional)
    if "output_path" in config:
        if not isinstance(config["output_path"], str):
            raise TypeError("output_path must be a string")
        validated["output_path"] = config["output_path"]
    else:
        # Default to input path with csv extension
        input_base = os.path.splitext(config["input_path"])[0]
        if input_base.endswith(".gz"):  # Handle gzipped files
            input_base = os.path.splitext(input_base)[0]
        validated["output_path"] = f"{input_base}_wells.csv"

    # Validate outer_bounds
    if "outer_bounds" in config and config["outer_bounds"] is not None:
        if (
            not isinstance(config["outer_bounds"], list)
            or len(config["outer_bounds"]) != 4
        ):
            raise TypeError(
                "outer_bounds must be a list of 4 numbers: [min_x, max_x, min_y, max_y]"
            )
        if not all(isinstance(x, (int, float)) for x in config["outer_bounds"]):
            raise TypeError("All values in outer_bounds must be numbers")
        validated["outer_bounds"] = tuple(config["outer_bounds"])
    else:
        validated["outer_bounds"] = None

    # Validate v_lines
    if "v_lines" not in config or not isinstance(config["v_lines"], list):
        raise TypeError("v_lines must be a list of numbers")
    if not all(isinstance(x, (int, float)) for x in config["v_lines"]):
        raise TypeError("All values in v_lines must be numbers")
    validated["v_lines"] = config["v_lines"]

    # Validate h_lines
    if "h_lines" not in config or not isinstance(config["h_lines"], list):
        raise TypeError("h_lines must be a list of numbers")
    if not all(isinstance(x, (int, float)) for x in config["h_lines"]):
        raise TypeError("All values in h_lines must be numbers")
    validated["h_lines"] = config["h_lines"]

    # Validate h_slope
    if "h_slope" in config:
        if not isinstance(config["h_slope"], (int, float)):
            raise TypeError("h_slope must be a number")
        validated["h_slope"] = float(config["h_slope"])
    else:
        validated["h_slope"] = 0.0

    # Validate v_slope
    if "v_slope" in config:
        if (
            not isinstance(config["v_slope"], (int, float))
            and config["v_slope"] != "inf"
        ):
            raise TypeError("v_slope must be a number or 'inf'")
        validated["v_slope"] = (
            float("inf") if config["v_slope"] == "inf" else float(config["v_slope"])
        )
    else:
        validated["v_slope"] = float("inf")

    # Validate visualization flag
    if "visualize" in config:
        validated["visualize"] = bool(config["visualize"])
    else:
        validated["visualize"] = False

    return validated


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a YAML file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return validate_config(config)
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")


def collapse_well_dfs(well_dfs):
    """Collapse well DataFrames into a single DataFrame with well information."""
    collapsed_df = pd.DataFrame()

    for well, sub_df in well_dfs.items():
        # Create a copy to avoid modifying the original
        temp_df = sub_df.copy()

        # Add well row and column as separate columns
        temp_df["well_row"] = well[0]
        temp_df["well_col"] = well[1]

        # Add a well_id column that combines row and column (e.g., "0_1")
        temp_df["well_id"] = f"{well[0]}_{well[1]}"

        # Append to the collapsed dataframe
        collapsed_df = pd.concat([collapsed_df, temp_df], ignore_index=True)

    # Sort by frame and particle for better organization
    collapsed_df = collapsed_df.sort_values(["frame", "particle"]).reset_index(
        drop=True
    )

    return collapsed_df


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Split tracking data by wells based on grid lines"
    )
    parser.add_argument("config", type=str, help="Path to YAML configuration file")
    args = parser.parse_args()

    # Load and validate configuration
    config = load_config(args.config)

    # Extract variables from config
    input_path = config["input_path"]
    output_path = config["output_path"]
    outer_bounds = config["outer_bounds"]
    v_lines = config["v_lines"]
    h_lines = config["h_lines"]
    h_slope = config["h_slope"]
    v_slope = config["v_slope"]
    visualize = config["visualize"]

    print(f"Loaded configuration from {args.config}")
    print(f"Input path: {input_path}")
    print(f"Output path: {output_path}")
    print(f"Outer bounds: {outer_bounds}")
    print(f"Vertical lines: {v_lines}")
    print(f"Horizontal lines: {h_lines}")
    print(f"Horizontal slope: {h_slope}")
    print(f"Vertical slope: {v_slope}")

    # Load your particle tracking data
    print(f"Loading data from {input_path}...")
    df = pd.read_pickle(input_path, compression="gzip")

    # Split the data by wells
    well_dfs = split_by_wells(
        df,
        h_lines,
        v_lines,
        outer_bounds=outer_bounds,
        h_slope=h_slope,
        v_slope=v_slope,
    )

    # Visualize the wells if requested
    if visualize:
        # Create visualization output path by replacing .csv extension with .png
        viz_output_path = os.path.splitext(output_path)[0] + ".png"

        visualize_wells(
            df,
            well_dfs,
            h_lines,
            v_lines,
            outer_bounds=outer_bounds,
            h_slope=h_slope,
            v_slope=v_slope,
            output_path=viz_output_path,
        )

    # Collapse well_dfs into a single DataFrame with well information
    collapsed_df = collapse_well_dfs(well_dfs)

    # Report on the result
    print(f"Collapsed DataFrame shape: {collapsed_df.shape}")
    print(f"Number of unique wells: {collapsed_df['well_id'].nunique()}")

    # Save collapsed_df to CSV file
    collapsed_df.to_csv(output_path, index=False)
    print(f"DataFrame successfully saved to: {output_path}")
    print(f"File size: {os.path.getsize(output_path)/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()
